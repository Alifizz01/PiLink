from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
from typing import Iterable

import time

from .logging_utils import get_logger

logger = get_logger(__name__)


def ensure_dirs(*paths: str) -> None:
    for path in paths:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def copytree(src: str, dst: str) -> None:
    logger.info("Copying %s -> %s", src, dst)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_path(src: str, dst: str) -> None:
    if os.path.isdir(src):
        copytree(src, dst)
    else:
        ensure_dirs(os.path.dirname(dst))
        logger.info("Copying file %s -> %s", src, dst)
        shutil.copy2(src, dst)


def available_gb(path: str) -> float:
    stats = shutil.disk_usage(path)
    return stats.free / (1024 ** 3)


def checksum_path(path: str, algorithm: str = "sha256") -> str:
    path = os.path.abspath(path)
    hash_obj = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def write_checksum_manifest(source_dir: str, manifest_path: str) -> None:
    entries: list[str] = []
    for root, _, files in os.walk(source_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            digest = checksum_path(file_path)
            rel = os.path.relpath(file_path, source_dir)
            entries.append(f"{digest}  {rel}")
    entries.sort()
    pathlib.Path(manifest_path).write_text("\n".join(entries), encoding="utf-8")


def prune_old_entries(root: str, keep_days: int) -> list[str]:
    pruned: list[str] = []
    root_path = pathlib.Path(root)
    if not root_path.exists():
        return pruned
    now = time.time()
    for path in root_path.iterdir():
        if not path.is_dir():
            continue
        mtime_days = (now - path.stat().st_mtime) / 86400
        if mtime_days > keep_days:
            shutil.rmtree(path)
            pruned.append(str(path))
    return pruned

