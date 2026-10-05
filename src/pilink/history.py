"""A transfer log people can read back: one JSON object per line."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field


@dataclass
class Record:
    when: str
    direction: str            # "pc-to-flash" | "flash-to-pc"
    ok: bool
    files: int = 0
    bytes: int = 0
    seconds: float = 0.0
    destination: str = ""
    verified: bool = False
    error: str = ""
    names: list = field(default_factory=list)   # first few file names, for the history screen


def path_for(staging_root: str) -> str:
    return os.path.join(staging_root, "history.jsonl")


def append(staging_root: str, rec: Record) -> None:
    os.makedirs(staging_root, exist_ok=True)
    with open(path_for(staging_root), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(rec)) + "\n")


def load(staging_root: str, limit: int = 100) -> list[Record]:
    try:
        with open(path_for(staging_root), encoding="utf-8") as fh:
            lines = fh.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            out.append(Record(**json.loads(line)))
        except (ValueError, TypeError):
            continue
    return out
