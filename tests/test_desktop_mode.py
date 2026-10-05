"""flash_mount: auto - Raspberry Pi OS with desktop, where the desktop's own
automounter puts the stick under /media/<user>/<label>."""
import os

import pytest

from pilink import flash
from pilink.errors import PiLinkError
from pilink.transfer_manager import TransferManager

from conftest import SAMPLE


def test_resolve_picks_the_usb_filesystem_under_media(monkeypatch):
    monkeypatch.setattr(flash, "_mounts", lambda: [
        ("/dev/mmcblk0p2", "/"), ("/dev/mmcblk0p1", "/boot/firmware"),
        ("/dev/sda1", "/media/alif/KINGSTON"), ("tmpfs", "/run/user/1000")])
    assert flash.resolve("auto") == "/media/alif/KINGSTON"
    assert flash.resolve("/mnt/flash") == "/mnt/flash"          # lite mode is untouched


def test_auto_mode_transfers_into_the_desktop_mount(setup, monkeypatch):
    cfg, pc, stick = setup
    cfg.paths.flash_mount = "auto"
    monkeypatch.setattr(flash, "AUTO_ROOTS", (str(stick.parent) + os.sep,))
    monkeypatch.setattr(flash, "_mounts", lambda: [("/dev/sdb1", str(stick))])
    res = TransferManager(cfg).run_pc_to_flash()
    assert res.verified and res.destination.startswith(str(stick / "transfers"))
    for rel, data in SAMPLE.items():
        assert (stick / "transfers" / os.path.basename(res.destination) / rel).read_bytes() == data


def test_auto_mode_with_no_stick_says_so(setup, monkeypatch):
    cfg, *_ = setup
    cfg.paths.flash_mount = "auto"
    monkeypatch.setattr(flash, "_mounts", lambda: [("/dev/mmcblk0p2", "/")])
    m = TransferManager(cfg)
    assert not m.flash_status().present
    with pytest.raises(PiLinkError, match="No flash drive"):
        m.run_pc_to_flash()
    assert "Nothing to eject" in m.eject()
