Operations & Runbooks
=====================

Boot & UI
---------

1. Power on the Pi. After a few seconds the BIOS-like UI launches automatically via `pilink-ui.service`.
2. The home screen shows:
   * Flash drive status (mounted? capacity?).
   * PC link status (ping + FTP auth check).
   * Last transfer summary and log tail.
3. Use the arrow keys or number shortcuts to choose:
   * `1 – Computer → Flash`
   * `2 – Flash → Computer`
   * `L – View logs`
   * `Q – Quit to shell`

Computer → Flash workflow
-------------------------

1. Choose `Computer → Flash`.
2. Select a remote preset (configured in `/etc/pilink.yaml`). Optionally specify a subfolder override.
3. The UI shows transfer metrics (bytes copied, throughput, ETA). Data lands in `/data/pc_inbox/<timestamp>`.
4. Once the pull completes, the USB watcher mirrors the folder to `/mnt/flash/transfers/<timestamp>`. Progress is reflected in the UI.
5. When finished, optionally eject the flash drive by pressing `E` on the home screen—this safely unmounts `/mnt/flash`.

Flash → Computer workflow
-------------------------

1. Choose `Flash → Computer`.
2. Browse the flash drive tree (arrow keys + space to select). Selections copy into `/data/flash_outbox/<timestamp>`.
3. Specify the PC destination preset. The Pi uploads the selection via FTP.
4. Completion triggers checksum verification (SHA-256). Results appear in the status panel.

Automatic USB mirroring
-----------------------

* `pilink.services.usb_watcher` uses watchdog to observe `/data/pc_inbox`.
* Any new folder triggers a copy to `/mnt/flash/transfers/<timestamp>` plus checksum generation in `checksums.txt`.
* Errors (e.g., disconnected drive) surface in both the log and UI. The watcher retries every 30 seconds until the mount returns.

Maintenance tasks
-----------------

* **Rotate logs** – `logrotate` config (example in `scripts/logrotate/pilink`) keeps `/var/log/pilink.log` under control. Run `sudo logrotate -f /etc/logrotate.d/pilink` if the file grows large.
* **Clear staging** – `TransferManager.prune_staging()` runs at boot plus manual trigger from the UI (`P` hotkey). Customize retention days in config.
* **Update software** – Pull latest repo changes, then `pip install -r requirements.txt --upgrade`.
* **Swap flash drive** – Quit the UI (`Q`), ensure `/mnt/flash` is unmounted, replace the drive, and re-open the UI.

Troubleshooting
---------------

| Symptom | Checks |
|---------|--------|
| UI says “PC offline” | Verify Ethernet link lights, run `ping 192.168.50.1`, confirm FTP credentials. |
| USB drive missing | `lsblk` to confirm device, check `/etc/fstab` or udev rule, look at `/var/log/syslog`. |
| Transfers hang mid-way | Inspect `/var/log/pilink.log`, confirm free space on both Pi and flash drive, verify FileZilla queue isn’t paused. |
| FTP login fails | Re-enter credentials in `/etc/pilink.yaml`, restart `pilink-ui` and `pilink-usb-watcher` services. |

Manual recovery commands
------------------------

```
sudo systemctl restart pilink-ui.service
sudo systemctl restart pilink-usb-watcher.service
sudo journalctl -u pilink-ui -u pilink-usb-watcher -f
python -m pilink.transfer_manager --dry-run
```

Testing checklist
-----------------

1. `pytest` (if tests are added) plus `python -m pilink.transfer_manager --self-test`.
2. Initiate both transfer modes with sample data; confirm checksums.
3. Unplug the flash drive mid-transfer to ensure the watcher pauses gracefully.
4. Reboot the Pi to confirm it lands back in the blue UI automatically.

