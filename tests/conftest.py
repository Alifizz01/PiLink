"""A real FTP server (pyftpdlib) standing in for FileZilla Server, plus temp
folders standing in for the Pi's SD card and the USB flash drive."""
import pathlib
import threading

import pytest
import yaml
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

from pilink.config import load_config


def write_tree(root: pathlib.Path, files: dict) -> None:
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


SAMPLE = {
    "report.pdf": b"%PDF-1.7 " + bytes(range(256)) * 400,
    "photos/a.jpg": b"\xff\xd8" + b"A" * 70_000,
    "photos/2026/b.jpg": b"\xff\xd8" + b"B" * 5_000,
    "notes.txt": b"hello from the PC\n",
}


@pytest.fixture
def ftp_server(tmp_path):
    pc = tmp_path / "pc"
    (pc / "computer_share").mkdir(parents=True)
    (pc / "uploads").mkdir()
    auth = DummyAuthorizer()
    auth.add_user("pilink", "secret", str(pc), perm="elradfmwMT")
    handler = type("H", (FTPHandler,), {"authorizer": auth, "banner": "test server"})
    server = ThreadedFTPServer(("127.0.0.1", 0), handler)
    port = server.socket.getsockname()[1]
    t = threading.Thread(target=server.serve_forever, kwargs={"timeout": 0.1}, daemon=True)
    t.start()
    yield pc, port
    server.close_all()


@pytest.fixture
def setup(tmp_path, ftp_server):
    """(config, pc_root, flash_root) with the sample files waiting on the PC."""
    pc, port = ftp_server
    write_tree(pc / "computer_share", SAMPLE)
    data, flash = tmp_path / "data", tmp_path / "flash"
    flash.mkdir()
    cfg = {
        "paths": {"staging_root": str(data), "pc_inbox": str(data / "pc_inbox"),
                  "flash_outbox": str(data / "flash_outbox"), "log_dir": str(data / "logs"),
                  "flash_mount": str(flash), "flash_transfer_root": str(flash / "transfers"),
                  "require_mount": False},
        "pc_endpoints": [{"name": "test-pc", "host": "127.0.0.1", "port": port, "username": "pilink",
                          "password": "secret", "download_root": "/computer_share",
                          "upload_root": "/uploads", "timeout": 5}],
    }
    path = tmp_path / "pilink.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return load_config(path), pc, flash
