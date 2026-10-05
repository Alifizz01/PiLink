"""`pilink demo`: the real UI on any computer, against a fake PC and a fake stick.

A local FTP server (pyftpdlib) plays FileZilla Server on the PC, a folder
plays the USB flash drive, and sample files are waiting. Nothing outside the
demo folder is touched.
"""
from __future__ import annotations

import logging
import os
import pathlib
import tempfile
import threading

import yaml

SAMPLE_PC = {
    "Project report Q3.pdf": 2_400_000,
    "Budget 2026.xlsx": 380_000,
    "Photos/site-visit-01.jpg": 3_100_000,
    "Photos/site-visit-02.jpg": 2_900_000,
    "Photos/site-visit-03.jpg": 3_300_000,
    "Firmware/controller-v2.4.bin": 1_048_576,
    "Firmware/release-notes.txt": 4_200,
}
SAMPLE_STICK = {
    "Measurements/run-001.csv": 640_000,
    "Measurements/run-002.csv": 655_000,
    "Measurements/run-003.csv": 702_000,
    "Logger/can-capture.mf4": 5_800_000,
    "Signed contract.pdf": 1_200_000,
    "System Volume Information/IndexerVolumeGuid": 76,
}


def _fill(root: pathlib.Path, files: dict) -> None:
    for rel, size in files.items():
        p = root / rel
        if p.exists():
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        seed = (rel * (size // max(len(rel), 1) + 1)).encode()[:size]
        p.write_bytes(seed)


def prepare(base: str | None = None, port: int = 0):
    """Create the demo world; returns (config path, ftp server, root)."""
    try:
        from pyftpdlib.authorizers import DummyAuthorizer
        from pyftpdlib.handlers import FTPHandler
        from pyftpdlib.servers import FTPServer
    except ImportError:
        raise SystemExit("The demo needs pyftpdlib:  pip install \"pilink[demo]\"   (or: pip install pyftpdlib)")
    root = pathlib.Path(base or os.path.join(tempfile.gettempdir(), "pilink-demo")).resolve()
    pc, stick, data = root / "pc", root / "flash-drive", root / "pi-data"
    (pc / "computer_share").mkdir(parents=True, exist_ok=True)
    (pc / "uploads").mkdir(exist_ok=True)
    _fill(pc / "computer_share", SAMPLE_PC)
    _fill(stick, SAMPLE_STICK)

    # pyftpdlib prints to the terminal unless its logger already has a handler;
    # that would scribble over the UI. Its messages go to PiLink's log file instead.
    logging.getLogger("pyftpdlib").addHandler(logging.NullHandler())
    auth = DummyAuthorizer()
    auth.add_user("pilink", "demo", str(pc), perm="elradfmwMT")
    handler = type("DemoHandler", (FTPHandler,), {"authorizer": auth, "banner": "PiLink demo PC"})
    server = FTPServer(("127.0.0.1", port), handler)
    port = server.socket.getsockname()[1]
    threading.Thread(target=server.serve_forever, kwargs={"timeout": 0.2}, daemon=True).start()

    cfg = {
        "paths": {"staging_root": str(data), "pc_inbox": str(data / "pc_inbox"),
                  "flash_outbox": str(data / "flash_outbox"), "log_dir": str(data / "logs"),
                  "flash_mount": str(stick), "flash_transfer_root": str(stick / "transfers"),
                  "require_mount": False},
        "pc_endpoints": [{"name": "office-pc", "host": "127.0.0.1", "port": port, "username": "pilink",
                          "password": "demo", "download_root": "/computer_share", "upload_root": "/uploads"}],
        "logging": {"log_file": str(data / "logs" / "pilink.log")},
    }
    path = root / "pilink-demo.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return path, server, root


def run_demo(base: str | None = None) -> int:
    from .config import load_config
    from .logging_utils import configure_logging
    from .ui.app import PiLinkApp

    path, server, root = prepare(base)
    cfg = load_config(path)
    configure_logging(cfg.logging.log_file, "INFO")
    try:
        PiLinkApp(cfg).run()
    finally:
        server.close_all()
    print(f"\nDemo files are in {root}\n  'PC':          {root / 'pc'}\n  'flash drive': {root / 'flash-drive'}")
    return 0
