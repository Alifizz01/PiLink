"""FTP / FTPS client for the PC side (FileZilla Server or any standard FTP server).

Every network failure is turned into a PiLinkError whose message says what
to check, because the person reading it is looking at the Pi's screen, not
at a traceback.
"""
from __future__ import annotations

import ftplib
import os
import posixpath
import socket
import ssl
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from .errors import PiLinkError
from .logging_utils import get_logger

logger = get_logger(__name__)

# (bytes_done, bytes_total, current_file)
ProgressCb = Callable[[int, int, str], None]
CHUNK = 64 * 1024


@dataclass
class RemoteFile:
    path: str            # absolute remote path
    rel: str             # path relative to the walked root, with "/"
    size: int


def explain(exc: BaseException, host: str, port: int) -> PiLinkError:
    """Turn a low-level error into one sentence a person can act on."""
    where = f"{host}:{port}"
    if isinstance(exc, PiLinkError):
        return exc
    if isinstance(exc, ConnectionRefusedError):
        return PiLinkError(f"The PC at {where} refused the connection. Is FileZilla Server running, "
                           f"and listening on port {port}?")
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return PiLinkError(f"No answer from {where}. Check the Ethernet cable, the PC's static IP, "
                           "and that Windows Firewall allows FileZilla Server (including its passive ports).")
    if isinstance(exc, OSError) and exc.errno in (101, 113, 10051, 10065):
        return PiLinkError(f"No route to {where}. Is the cable plugged in and does the Pi have its static IP?")
    if isinstance(exc, ftplib.error_perm):
        text = str(exc)
        if text.startswith("530"):
            if "TLS" in text or "SSL" in text or "AUTH" in text:
                return PiLinkError("The PC requires encrypted FTP. Set tls: true for this endpoint "
                                   "in /etc/pilink.yaml (FileZilla Server 1.x does this by default).")
            return PiLinkError("The PC rejected the username or password. Check the user in FileZilla Server "
                               "against pc_endpoints in /etc/pilink.yaml.")
        if text.startswith("550"):
            return PiLinkError(f"The PC refused access to a folder: {text[4:]}. Check that the folder exists "
                               "and the FileZilla user has read/write permission on it.")
        return PiLinkError(f"The PC's FTP server refused the request: {text}")
    if isinstance(exc, ssl.SSLError):
        return PiLinkError(f"Encrypted FTP failed ({exc.reason}). Check the TLS settings in FileZilla Server, "
                           "or set tls: false if the server does not use TLS.")
    if isinstance(exc, (ftplib.error_temp, ftplib.error_reply, ftplib.error_proto)):
        return PiLinkError(f"The PC's FTP server reported a problem: {exc}")
    if isinstance(exc, OSError):
        return PiLinkError(f"Network error talking to {where}: {exc.strerror or exc}")
    return PiLinkError(f"Unexpected error talking to {where}: {exc}")


class FTPClient:
    def __init__(self, host: str, port: int = 21, username: str = "", password: str = "",
                 tls: bool = False, timeout: int = 20) -> None:
        self.host, self.port, self.tls, self.timeout = host, port, tls, timeout
        self.username, self.password = username, password
        self.ftp: Optional[ftplib.FTP] = None

    @classmethod
    def for_endpoint(cls, ep) -> "FTPClient":
        return cls(ep.host, ep.port, ep.username, ep.password, ep.tls, ep.timeout)

    def __enter__(self) -> "FTPClient":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _wrap(self, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:          # translated, never swallowed
            raise explain(exc, self.host, self.port) from exc

    def connect(self) -> None:
        def go():
            ftp = ftplib.FTP_TLS(timeout=self.timeout) if self.tls else ftplib.FTP(timeout=self.timeout)
            ftp.connect(self.host, self.port)
            ftp.login(self.username, self.password)
            if self.tls:
                ftp.prot_p()                # encrypt the data channel too
            ftp.set_pasv(True)
            return ftp
        logger.info("connecting to %s:%s%s", self.host, self.port, " (TLS)" if self.tls else "")
        self.ftp = self._wrap(go)

    def close(self) -> None:
        if self.ftp is not None:
            try:
                self.ftp.quit()
            except Exception:
                self.ftp.close()
            self.ftp = None

    # ------------------------------------------------------------------ listing
    def _entries(self, path: str) -> Iterator[tuple[str, bool, int]]:
        """(name, is_dir, size) for one remote directory. MLSD where the server
        has it (FileZilla Server does); a LIST parser otherwise."""
        try:
            for name, facts in self.ftp.mlsd(path, facts=["type", "size"]):
                kind = facts.get("type", "")
                if kind in ("cdir", "pdir") or name in (".", ".."):
                    continue
                yield name, kind == "dir", int(facts.get("size", 0) or 0)
        except ftplib.error_perm as exc:
            if not str(exc).startswith("500") and not str(exc).startswith("502"):
                raise
            lines: list[str] = []
            self.ftp.retrlines(f"LIST {path}", lines.append)
            for line in lines:
                parts = line.split(None, 8)
                if len(parts) < 9 or parts[8] in (".", ".."):
                    continue
                yield parts[8], line.startswith("d"), int(parts[4]) if parts[4].isdigit() else 0

    def walk(self, root: str) -> list[RemoteFile]:
        """Every file below root, recursively, with sizes."""
        def go():
            out, stack = [], [""]
            while stack:
                rel_dir = stack.pop()
                here = posixpath.join(root, rel_dir) if rel_dir else root
                for name, is_dir, size in self._entries(here):
                    rel = posixpath.join(rel_dir, name) if rel_dir else name
                    if is_dir:
                        stack.append(rel)
                    else:
                        out.append(RemoteFile(posixpath.join(root, rel), rel, size))
            return sorted(out, key=lambda f: f.rel)
        return self._wrap(go)

    # ----------------------------------------------------------------- transfer
    def download(self, files: list[RemoteFile], local_dir: str, progress: Optional[ProgressCb] = None) -> int:
        total = sum(f.size for f in files)
        done = 0
        for f in files:
            dest = os.path.join(local_dir, *f.rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as fh:
                def sink(block, fh=fh, name=f.rel):
                    nonlocal done
                    fh.write(block)
                    done += len(block)
                    if progress:
                        progress(done, total, name)
                self._wrap(self.ftp.retrbinary, f"RETR {f.path}", sink, CHUNK)
            if progress:
                progress(done, total, f.rel)
        return done

    def ensure_dir(self, remote_path: str) -> None:
        """mkdir -p on the server."""
        current = "" if not remote_path.startswith("/") else "/"
        for part in [p for p in remote_path.split("/") if p]:
            current = posixpath.join(current, part)
            try:
                self.ftp.mkd(current)
            except ftplib.error_perm as exc:
                if not str(exc).startswith("550"):     # 550: already there
                    raise explain(exc, self.host, self.port) from exc

    def upload(self, pairs: list[tuple[str, str]], progress: Optional[ProgressCb] = None) -> int:
        """pairs: (local file, remote path). Creates remote folders as needed."""
        total = sum(os.path.getsize(src) for src, _ in pairs)
        done = 0
        made: set[str] = set()
        for src, remote in pairs:
            folder = posixpath.dirname(remote)
            if folder not in made:
                self.ensure_dir(folder)
                made.add(folder)

            def tick(block, name=remote):
                nonlocal done
                done += len(block)
                if progress:
                    progress(done, total, name)
            with open(src, "rb") as fh:
                self._wrap(self.ftp.storbinary, f"STOR {remote}", fh, CHUNK, tick)
        return done

    def size(self, remote_path: str) -> Optional[int]:
        """Remote file size, or None if the server will not say."""
        try:
            self.ftp.voidcmd("TYPE I")
            return self.ftp.size(remote_path)
        except ftplib.all_errors:
            return None

    def ping(self) -> None:
        """Connect, log in, look at the download folder; raise PiLinkError otherwise."""
        self._wrap(self.ftp.voidcmd, "NOOP")
