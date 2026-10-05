import hashlib
import os
import threading

import pytest
import yaml

from pilink import history
from pilink.config import ConfigError, load_config
from pilink.errors import PiLinkError
from pilink.transfer_manager import TransferManager

from conftest import SAMPLE, write_tree


def test_pc_to_flash_copies_everything_and_verifies(setup):
    cfg, pc, flash = setup
    events = []
    res = TransferManager(cfg).run_pc_to_flash(progress=events.append)
    assert res.verified and res.files == len(SAMPLE) and res.bytes == sum(map(len, SAMPLE.values()))
    for rel, data in SAMPLE.items():
        assert (flash / "transfers").joinpath(os.path.basename(res.destination), rel).read_bytes() == data
    manifest = (flash / "transfers" / os.path.basename(res.destination) / "checksums.txt").read_text()
    assert f"{hashlib.sha256(SAMPLE['notes.txt']).hexdigest()}  notes.txt" in manifest
    phases = [e.phase for e in events]
    assert phases.index("download") < phases.index("copy") < phases.index("verify") < phases.index("done")
    downloads = [e for e in events if e.phase == "download"]
    assert downloads[-1].done == downloads[-1].total == res.bytes        # byte-accurate progress


def test_flash_to_pc_uploads_selection_into_a_dated_folder(setup):
    cfg, pc, flash = setup
    write_tree(flash, {"docs/a.txt": b"a" * 1000, "docs/sub/b.bin": bytes(3000), "single.txt": b"x",
                       "System Volume Information/IndexerVolumeGuid": b"junk"})
    m = TransferManager(cfg)
    res = m.run_flash_to_pc(["docs", "single.txt"])
    assert res.verified and res.files == 3
    remote = next((pc / "uploads").iterdir())
    assert (remote / "docs" / "sub" / "b.bin").read_bytes() == bytes(3000)
    assert (remote / "single.txt").read_bytes() == b"x"
    assert (remote / "checksums.txt").exists()
    # whole stick: the system folder is never sent
    res = m.run_flash_to_pc([str(flash)])
    assert not any("System Volume" in n for n in res.names)


def test_second_upload_does_not_overwrite_the_first(setup, monkeypatch):
    cfg, pc, flash = setup
    write_tree(flash, {"f.txt": b"one"})
    m = TransferManager(cfg)
    stamps = iter(["20260101-000001", "20260101-000002"])
    monkeypatch.setattr(m, "_stamp", lambda: next(stamps))
    m.run_flash_to_pc(["f.txt"])
    (flash / "f.txt").write_bytes(b"two")
    m.run_flash_to_pc(["f.txt"])
    assert (pc / "uploads/20260101-000001/f.txt").read_bytes() == b"one"
    assert (pc / "uploads/20260101-000002/f.txt").read_bytes() == b"two"


def test_wrong_password_says_what_to_check(setup):
    cfg, *_ = setup
    cfg.pc_endpoints[0].password = "wrong"
    with pytest.raises(PiLinkError, match="username or password"):
        TransferManager(cfg).run_pc_to_flash()
    rec = history.load(cfg.paths.staging_root)[0]
    assert not rec.ok and "password" in rec.error                # failures are in the history too


def test_pc_not_reachable_says_what_to_check(setup):
    cfg, *_ = setup
    cfg.pc_endpoints[0].port = 1
    with pytest.raises(PiLinkError, match="refused|No answer|No route"):
        TransferManager(cfg).run_pc_to_flash()


def test_refuses_to_write_when_no_drive_is_mounted(setup):
    cfg, pc, flash = setup
    cfg.paths.require_mount = True                 # a temp folder is not a mount point
    with pytest.raises(PiLinkError, match="No flash drive"):
        TransferManager(cfg).run_pc_to_flash()
    assert not (flash / "transfers").exists()     # nothing written "to the stick" that is really the SD card


def test_empty_pc_folder_and_empty_selection(setup):
    cfg, pc, flash = setup
    for f in (pc / "computer_share").rglob("*"):
        if f.is_file():
            f.unlink()
    with pytest.raises(PiLinkError, match="empty"):
        TransferManager(cfg).run_pc_to_flash()
    with pytest.raises(PiLinkError, match="Nothing selected"):
        TransferManager(cfg).run_flash_to_pc([])


def test_selection_outside_the_stick_is_refused(setup, tmp_path):
    cfg, *_ = setup
    outside = tmp_path / "secret.txt"
    outside.write_text("no")
    with pytest.raises(PiLinkError, match="not on the flash drive"):
        TransferManager(cfg).run_flash_to_pc([str(outside)])


def test_not_enough_space_is_reported_before_anything_is_copied(setup, monkeypatch):
    cfg, pc, flash = setup
    monkeypatch.setattr("pilink.storage.free_bytes", lambda path: 10)
    with pytest.raises(PiLinkError, match="Not enough space"):
        TransferManager(cfg).run_pc_to_flash()
    assert not (flash / "transfers").exists()


def test_corruption_on_the_stick_is_caught(setup, monkeypatch):
    cfg, *_ = setup
    real = __import__("pilink.storage", fromlist=["x"]).copy_files

    def flaky(pairs, progress=None):
        n = real(pairs, progress)
        with open(pairs[0][1], "r+b") as fh:          # a bad sector flips a byte after writing
            fh.write(b"\x00")
        return n
    monkeypatch.setattr("pilink.storage.copy_files", flaky)
    with pytest.raises(PiLinkError, match="Verification failed"):
        TransferManager(cfg).run_pc_to_flash()


def test_cancel(setup):
    cfg, *_ = setup
    stop = threading.Event()
    stop.set()
    with pytest.raises(PiLinkError, match="Cancelled"):
        TransferManager(cfg).run_pc_to_flash(cancel=stop)


def test_config_errors_name_the_key(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({"paths": {}, "pc_endpoints": [{"name": "pc", "host": "h"}]}))
    with pytest.raises(ConfigError, match=r"pc_endpoints\[0\]: missing username, password"):
        load_config(p)
    p.write_text(yaml.safe_dump({"paths": {"flash_mount": "/mnt/flash", "typo": 1},
                                 "pc_endpoints": [{"name": "pc", "host": "h", "username": "u", "password": "p"}]}))
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(p)


def test_the_2025_example_config_still_loads():
    cfg = load_config(os.path.join(os.path.dirname(__file__), "legacy_config_2025.yaml"))
    assert cfg.default_endpoint.host == "192.168.50.1"
