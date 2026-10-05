"""`pilink doctor` and the Diagnostics screen: every check says what to do when it fails."""
from __future__ import annotations

import os
import shutil
import socket

from . import flash
from .config import Config
from .errors import PiLinkError
from .storage import human


def run_checks(cfg: Config) -> list[tuple[bool | None, str, str]]:
    """(ok, name, detail). ok=None means a warning, not a failure."""
    out: list[tuple[bool | None, str, str]] = []
    p = cfg.paths

    for label, path in (("Pi staging folder", p.staging_root), ("Log folder", p.log_dir)):
        try:
            os.makedirs(path, exist_ok=True)
            ok = os.access(path, os.W_OK)
            out.append((ok, label, f"{path}: {human(shutil.disk_usage(path).free)} free" if ok
                        else f"{path} is not writable by this user; rerun setup_pi.sh"))
        except OSError as exc:
            out.append((False, label, f"{path}: {exc}"))

    st = flash.status(flash.resolve(p.flash_mount), p.require_mount)
    if st.present and st.writable:
        out.append((True, "Flash drive", f"{st.label} at {st.mount}: {human(st.free)} free of {human(st.total)}"))
    elif st.present:
        out.append((False, "Flash drive", st.note))
    else:
        out.append((None, "Flash drive", st.note + " (needed for transfers, not for this check)"))

    for ep in cfg.pc_endpoints:
        name = f"PC '{ep.name}' network"
        try:
            with socket.create_connection((ep.host, ep.port), timeout=min(ep.timeout, 5)):
                out.append((True, name, f"{ep.host}:{ep.port} answers"))
        except OSError as exc:
            out.append((False, name, f"{ep.host}:{ep.port} does not answer ({exc.strerror or exc}). "
                                     "Check the cable, both static IPs and that FileZilla Server is running."))
            continue
        try:
            from .transfer_manager import TransferManager
            summary = TransferManager(cfg).check_pc(ep.name)
            out.append((True, f"PC '{ep.name}' FTP login", f"{'FTPS' if ep.tls else 'FTP'} as {ep.username}: {summary}"))
        except PiLinkError as exc:
            out.append((False, f"PC '{ep.name}' FTP login", str(exc)))
    return out
