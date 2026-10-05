"""The USB flash drive: is it really there, how much room, and safe removal."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from .errors import PiLinkError
from .logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class FlashStatus:
    present: bool
    mount: str
    label: str = ""
    total: int = 0
    free: int = 0
    writable: bool = False
    note: str = ""


def _label(mount: str) -> str:
    """Volume label from /proc/mounts + /dev/disk/by-label, if the system has them."""
    try:
        dev = next(line.split()[0] for line in open("/proc/mounts", encoding="utf-8")
                   if line.split()[1] == mount)
        by_label = "/dev/disk/by-label"
        for name in os.listdir(by_label):
            if os.path.realpath(os.path.join(by_label, name)) == os.path.realpath(dev):
                return name.replace("\\x20", " ")
    except (OSError, StopIteration):
        pass
    return ""


AUTO_ROOTS = ("/media/", "/run/media/")


def _mounts() -> list[tuple[str, str]]:
    """(device, mount point) from /proc/mounts; empty where there is none (Windows demo)."""
    try:
        with open("/proc/mounts", encoding="utf-8") as fh:
            rows = [line.split()[:2] for line in fh]
    except OSError:
        return []
    return [(dev, mnt.replace("\\040", " ")) for dev, mnt in rows]


def resolve(configured: str) -> str:
    """The mount point to use. "auto" (Pi OS with desktop) means wherever the
    desktop's automounter put the stick: the first USB filesystem under
    /media/<user>/. Returns "" when nothing is mounted there."""
    if configured != "auto":
        return configured
    found = sorted(mnt for dev, mnt in _mounts()
                   if mnt.startswith(AUTO_ROOTS) and dev.startswith("/dev/sd"))
    return found[0] if found else ""


def status(mount: str, require_mount: bool = True) -> FlashStatus:
    if not mount:
        return FlashStatus(False, "", note="No flash drive. Plug one in; the desktop mounts it automatically.")
    if require_mount and not os.path.ismount(mount):
        return FlashStatus(False, mount, note="No flash drive. Plug one in; it mounts automatically.")
    if not os.path.isdir(mount):
        return FlashStatus(False, mount, note=f"{mount} does not exist.")
    usage = shutil.disk_usage(mount)
    writable = os.access(mount, os.W_OK)
    return FlashStatus(True, mount, _label(mount) or os.path.basename(mount.rstrip("/")) or mount,
                       usage.total, usage.free, writable,
                       "" if writable else "The drive is mounted read-only or not writable by PiLink.")


def require(mount: str, require_mount: bool = True) -> FlashStatus:
    st = status(mount, require_mount)
    if not st.present:
        raise PiLinkError(st.note)
    if not st.writable:
        raise PiLinkError(st.note)
    return st


def eject(mount: str, require_mount: bool = True) -> str:
    """Flush everything to the stick, then unmount it so it can be pulled safely."""
    if require_mount and not os.path.ismount(mount):
        return "Nothing to eject: no flash drive is mounted."
    if not mount:
        return "Nothing to eject: no flash drive is mounted."
    getattr(os, "sync", lambda: None)()        # os.sync does not exist on Windows (demo mode)
    if not require_mount:                      # demo / test: nothing real to unmount
        return "Flash drive synced. (Demo mode: not unmounted.)"
    if mount.startswith(AUTO_ROOTS):
        return _eject_udisks(mount)
    for cmd in (["sudo", "-n", "/usr/bin/systemd-umount", mount], ["sudo", "-n", "/usr/bin/umount", mount]):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("eject via %s failed: %s", cmd[2], exc)
            continue
        if res.returncode == 0 and not os.path.ismount(mount):
            logger.info("ejected %s", mount)
            return "Safe to remove the flash drive."
        logger.warning("eject via %s failed: %s", cmd[2], res.stderr.strip())
    raise PiLinkError("Could not unmount the flash drive (is a file on it still open?). "
                      "Everything has been written to it, but wait for the drive's light to stop before pulling it.")


def _eject_udisks(mount: str) -> str:
    """Pi OS with desktop: unmount the way the desktop's eject button does (no
    sudo), then power the stick off so it can be pulled."""
    dev = next((d for d, m in _mounts() if m == mount), "")
    if not dev:
        return "Nothing to eject: no flash drive is mounted."
    res = subprocess.run(["udisksctl", "unmount", "-b", dev], capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise PiLinkError(f"Could not unmount the flash drive ({res.stderr.strip() or 'busy'}). "
                          "Close any window showing its files and try again.")
    disk = dev.rstrip("0123456789")
    subprocess.run(["udisksctl", "power-off", "-b", disk], capture_output=True, text=True, timeout=30)
    logger.info("ejected %s (%s) via udisks", mount, dev)
    return "Safe to remove the flash drive."
