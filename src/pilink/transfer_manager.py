"""The two workflows, end to end, with every step checked.

Computer -> Flash
    flash present? -> list the PC folder -> enough space? -> download to staging
    -> sizes match the listing? -> hash -> copy to the stick (fsync) -> re-read
    and compare every hash -> checksums.txt on the stick

Flash -> Computer
    selection -> stage it -> hash -> upload into a new dated folder on the PC
    -> every remote size checked -> checksums.txt uploaded alongside

Nothing reports success until the verification step has passed, and every
transfer, failed or not, is written to the history.
"""
from __future__ import annotations

import datetime as dt
import os
import posixpath
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from . import flash, history, storage
from .config import Config
from .errors import PiLinkError
from .ftp_client import FTPClient
from .logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class Progress:
    phase: str          # connect | list | download | hash | copy | verify | stage | upload | done
    done: int = 0
    total: int = 0
    file: str = ""
    message: str = ""


@dataclass
class Result:
    direction: str
    files: int
    bytes: int
    seconds: float
    destination: str
    verified: bool
    names: list


ProgressHook = Callable[[Progress], None]
PHASES = {
    "connect": "Connecting to the PC",
    "list": "Reading the PC folder",
    "download": "Downloading from the PC",
    "hash": "Computing checksums",
    "copy": "Writing to the flash drive",
    "verify": "Verifying",
    "stage": "Reading the flash drive",
    "upload": "Uploading to the PC",
    "done": "Done",
}


class Cancelled(PiLinkError):
    pass


class TransferManager:
    def __init__(self, config: Config):
        self.config = config
        p = config.paths
        # Only Pi-side folders. Never create anything under the flash mount
        # point here: that is how files used to end up on the SD card.
        storage.ensure_dirs(p.staging_root, p.pc_inbox, p.flash_outbox, p.log_dir)

    # ------------------------------------------------------------------ helpers
    def _stamp(self) -> str:
        return dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    def _reporter(self, progress: Optional[ProgressHook], cancel: Optional[threading.Event]):
        def report(phase, done=0, total=0, file="", message=""):
            if cancel is not None and cancel.is_set():
                raise Cancelled("Cancelled. Nothing was reported as transferred; partial files stay in staging.")
            if progress:
                progress(Progress(phase, done, total, file, message or PHASES.get(phase, phase)))
        return report

    def mount(self) -> str:
        """Where the stick is right now ("" if nowhere): the configured path,
        or with flash_mount: auto, wherever the desktop mounted it."""
        return flash.resolve(self.config.paths.flash_mount)

    def transfer_root(self, mount: str) -> str:
        if self.config.paths.flash_mount == "auto":
            name = os.path.basename(self.config.paths.flash_transfer_root.rstrip("/")) or "transfers"
            return os.path.join(mount, name)
        return self.config.paths.flash_transfer_root

    def _flash(self):
        return flash.require(self.mount(), self.config.paths.require_mount)

    def _record(self, direction, started, ok, result: Optional[Result] = None, error: str = ""):
        rec = history.Record(
            when=dt.datetime.now().isoformat(timespec="seconds"), direction=direction, ok=ok,
            seconds=round(time.monotonic() - started, 2), error=error)
        if result:
            rec.files, rec.bytes, rec.destination = result.files, result.bytes, result.destination
            rec.verified, rec.names = result.verified, result.names[:5]
        history.append(self.config.paths.staging_root, rec)

    def _space(self, where: str, label: str, need: int) -> None:
        free = storage.free_bytes(where)
        if free < need + 1024 * 1024:
            raise PiLinkError(f"Not enough space on {label}: the transfer needs {storage.human(need)}, "
                              f"{storage.human(free)} is free.")

    def _run(self, direction, fn):
        started = time.monotonic()
        try:
            result = fn()
        except PiLinkError as exc:
            self._record(direction, started, False, error=str(exc))
            raise
        except Exception as exc:
            logger.exception("%s failed", direction)
            self._record(direction, started, False, error=str(exc))
            raise PiLinkError(f"Unexpected error: {exc}. Details are in the log.") from exc
        result.seconds = round(time.monotonic() - started, 2)
        self._record(direction, started, True, result)
        storage.prune(self.config.paths.pc_inbox, self.config.paths.retention_days)
        storage.prune(self.config.paths.flash_outbox, self.config.paths.retention_days)
        return result

    # ------------------------------------------------------------ PC -> flash
    def run_pc_to_flash(self, endpoint_name: Optional[str] = None, progress: Optional[ProgressHook] = None,
                        cancel: Optional[threading.Event] = None) -> Result:
        return self._run("pc-to-flash", lambda: self._pc_to_flash(endpoint_name, progress, cancel))

    def _pc_to_flash(self, endpoint_name, progress, cancel) -> Result:
        report = self._reporter(progress, cancel)
        ep = self.config.endpoint(endpoint_name)
        mount = self._flash().mount
        stamp = self._stamp()
        staging = os.path.join(self.config.paths.pc_inbox, stamp)
        dest = os.path.join(self.transfer_root(mount), stamp)

        report("connect", message=f"Connecting to {ep.name} ({ep.host})")
        with FTPClient.for_endpoint(ep) as ftp:
            report("list")
            files = ftp.walk(ep.download_root)
            if not files:
                raise PiLinkError(f"Nothing to copy: the PC folder {ep.download_root} is empty.")
            total = sum(f.size for f in files)
            self._space(self.config.paths.pc_inbox, "the Pi's SD card", total)
            self._space(mount, "the flash drive", total)
            os.makedirs(staging, exist_ok=True)
            ftp.download(files, staging, lambda d, t, n: report("download", d, t, n))

        for f in files:            # the listing said how big each file is: hold the server to it
            got = os.path.getsize(os.path.join(staging, *f.rel.split("/")))
            if f.size and got != f.size:
                raise PiLinkError(f"{f.rel} arrived with {got} bytes, the PC listed {f.size}. "
                                  "The transfer was interrupted; run it again.")

        report("hash", 0, len(files))
        hashes = storage.hash_tree(staging)
        pairs = [(full, os.path.join(dest, *rel.split("/"))) for full, rel in storage.list_files(staging)]
        storage.copy_files(pairs, lambda d, t, n: report("copy", d, t, n))

        for i, (rel, digest) in enumerate(sorted(hashes.items()), 1):
            report("verify", i, len(hashes), rel)
            if storage.sha256(os.path.join(dest, *rel.split("/"))) != digest:
                raise PiLinkError(f"Verification failed for {rel} on the flash drive: the copy differs from "
                                  "what was downloaded. The drive may be failing; try another one.")
        storage.write_manifest(hashes, os.path.join(dest, "checksums.txt"))
        getattr(os, "sync", lambda: None)()
        report("done", total, total)
        logger.info("pc-to-flash: %d files, %d bytes -> %s (verified)", len(files), total, dest)
        return Result("pc-to-flash", len(files), total, 0, dest, True, [f.rel for f in files])

    # ------------------------------------------------------------ flash -> PC
    def flash_entries(self, rel: str = "") -> list[tuple[str, bool, int]]:
        """(name, is_dir, size) in a folder on the stick, for the file picker."""
        base = os.path.join(self.mount(), rel)
        hidden = set(self.config.flash_drive.hidden)
        out = []
        for entry in sorted(os.scandir(base), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name in hidden or entry.name.startswith("."):
                continue
            size = 0 if entry.is_dir() else entry.stat().st_size
            out.append((entry.name, entry.is_dir(), size))
        return out

    def run_flash_to_pc(self, selections: list[str] | str, endpoint_name: Optional[str] = None,
                        progress: Optional[ProgressHook] = None, cancel: Optional[threading.Event] = None) -> Result:
        if isinstance(selections, str):
            selections = [selections]
        return self._run("flash-to-pc", lambda: self._flash_to_pc(list(selections), endpoint_name, progress, cancel))

    def _flash_to_pc(self, selections, endpoint_name, progress, cancel) -> Result:
        report = self._reporter(progress, cancel)
        ep = self.config.endpoint(endpoint_name)
        mount = os.path.realpath(self._flash().mount)
        if not selections:
            raise PiLinkError("Nothing selected. Pick files or folders on the flash drive first.")
        hidden = set(self.config.flash_drive.hidden)

        pairs: list[tuple[str, str]] = []          # (file on the stick, relative name)
        for sel in selections:
            full = os.path.realpath(sel if os.path.isabs(sel) else os.path.join(mount, sel))
            if not (full == mount or full.startswith(mount + os.sep)):
                raise PiLinkError(f"{sel} is not on the flash drive.")
            if not os.path.exists(full):
                raise PiLinkError(f"{sel} no longer exists on the flash drive.")
            if os.path.isdir(full):
                top = "" if full == mount else os.path.basename(full)
                for f, rel in storage.list_files(full):
                    if not any(part in hidden for part in rel.split("/")):
                        pairs.append((f, posixpath.join(top, rel) if top else rel))
            else:
                pairs.append((full, os.path.basename(full)))
        if not pairs:
            raise PiLinkError("The selection contains no files.")

        stamp = self._stamp()
        staging = os.path.join(self.config.paths.flash_outbox, stamp)
        total = sum(os.path.getsize(f) for f, _ in pairs)
        self._space(self.config.paths.flash_outbox, "the Pi's SD card", total)
        storage.copy_files([(f, os.path.join(staging, *rel.split("/"))) for f, rel in pairs],
                           lambda d, t, n: report("stage", d, t, n))
        report("hash", 0, len(pairs))
        hashes = storage.hash_tree(staging)
        manifest = os.path.join(staging, "checksums.txt")
        storage.write_manifest(hashes, manifest)

        remote_root = posixpath.join(ep.upload_root, stamp)
        uploads = [(os.path.join(staging, *rel.split("/")), posixpath.join(remote_root, rel))
                   for rel in sorted(hashes)] + [(manifest, posixpath.join(remote_root, "checksums.txt"))]
        report("connect", message=f"Connecting to {ep.name} ({ep.host})")
        with FTPClient.for_endpoint(ep) as ftp:
            ftp.upload(uploads, lambda d, t, n: report("upload", d, t, n))
            verified = True
            for i, (local, remote) in enumerate(uploads, 1):
                report("verify", i, len(uploads), posixpath.basename(remote))
                size = ftp.size(remote)
                if size is None:
                    verified = False                # server will not say; reported, not hidden
                elif size != os.path.getsize(local):
                    raise PiLinkError(f"{remote} on the PC has {size} bytes, expected {os.path.getsize(local)}. "
                                      "Run the transfer again.")
        report("done", total, total)
        logger.info("flash-to-pc: %d files, %d bytes -> %s:%s (sizes %s)", len(pairs), total, ep.host,
                    remote_root, "verified" if verified else "not reported by server")
        return Result("flash-to-pc", len(pairs), total, 0, f"{ep.name}:{remote_root}", verified,
                      [rel for _, rel in pairs])

    # ------------------------------------------------------------- status
    def check_pc(self, endpoint_name: Optional[str] = None) -> str:
        """One line for the dashboard; raises PiLinkError when the PC is not usable."""
        ep = self.config.endpoint(endpoint_name)
        with FTPClient.for_endpoint(ep) as ftp:
            files = ftp.walk(ep.download_root)
        size = sum(f.size for f in files)
        return f"{len(files)} file(s), {storage.human(size)} waiting in {ep.download_root}"

    def flash_status(self) -> flash.FlashStatus:
        return flash.status(self.mount(), self.config.paths.require_mount)

    def eject(self) -> str:
        return flash.eject(self.mount(), self.config.paths.require_mount)
