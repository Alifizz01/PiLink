"""Local files: hashing, copying with progress, space checks, staging cleanup."""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import time
from typing import Callable, Iterable, Optional

from .logging_utils import get_logger

logger = get_logger(__name__)
ProgressCb = Callable[[int, int, str], None]
CHUNK = 1024 * 1024


def ensure_dirs(*paths: str) -> None:
    for path in paths:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def list_files(root: str) -> list[tuple[str, str]]:
    """(absolute path, relative path with '/') for every file below root, sorted."""
    out = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            out.append((full, os.path.relpath(full, root).replace(os.sep, "/")))
    return out


def hash_tree(root: str) -> dict[str, str]:
    return {rel: sha256(full) for full, rel in list_files(root)}


def tree_size(paths: Iterable[str]) -> int:
    total = 0
    for p in paths:
        if os.path.isdir(p):
            total += sum(os.path.getsize(f) for f, _ in list_files(p))
        elif os.path.isfile(p):
            total += os.path.getsize(p)
    return total


def copy_files(pairs: list[tuple[str, str]], progress: Optional[ProgressCb] = None) -> int:
    """Copy (src, dst) pairs with byte progress, fsync'ing every file so that
    'copied' means 'on the device', not 'in the page cache'."""
    total = sum(os.path.getsize(src) for src, _ in pairs)
    done = 0
    for src, dst in pairs:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "rb") as fin, open(dst, "wb") as fout:
            for chunk in iter(lambda: fin.read(CHUNK), b""):
                fout.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total, os.path.basename(dst))
            fout.flush()
            os.fsync(fout.fileno())
        try:
            shutil.copystat(src, dst)          # keep modification times; FAT may refuse some
        except OSError:
            pass
    return done


def write_manifest(hashes: dict[str, str], path: str) -> None:
    """sha256sum-compatible: `sha256sum -c checksums.txt` works on any Linux."""
    lines = [f"{digest}  {rel}" for rel, digest in sorted(hashes.items())]
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def free_bytes(path: str) -> int:
    while not os.path.exists(path):          # a folder that will be created: ask its parent
        path = os.path.dirname(path) or "/"
    return shutil.disk_usage(path).free


def prune(root: str, keep_days: int) -> list[str]:
    """Delete staging folders older than keep_days. Returns what was removed."""
    removed: list[str] = []
    base = pathlib.Path(root)
    if not base.exists() or keep_days < 0:
        return removed
    cutoff = time.time() - keep_days * 86400
    for entry in base.iterdir():
        if entry.is_dir() and entry.stat().st_mtime < cutoff:
            shutil.rmtree(entry, ignore_errors=True)
            removed.append(str(entry))
    if removed:
        logger.info("pruned %d staging folder(s) older than %d days from %s", len(removed), keep_days, root)
    return removed


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
