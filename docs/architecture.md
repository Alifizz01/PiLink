Architecture Overview
=====================

Goals
-----

* Provide an appliance-like experience: when the Pi boots, a BIOS-style UI becomes the default shell.
* Offer two automated transfer flows with zero manual file management.
* Keep the PC ↔ Pi link isolated and deterministic by using a direct Ethernet cable with static IPs.
* Mirror everything onto a USB flash drive that attaches to the Pi and auto-mounts.

Key components
--------------

### Networking

* Dedicated Ethernet cable between Windows PC and Raspberry Pi.
* Static IP scheme (example): `PC 192.168.50.1/24`, `Pi 192.168.50.2/24`.
* Optional DHCP server on the Pi if you want the PC to obtain settings automatically.
* Firewall rules on both sides restrict FTP traffic to the dedicated NIC.

### FTP services

* **On Pi**: `vsftpd` accepts inbound FTP transfers should you ever need to push from the PC manually.
* **On PC**: FileZilla Server (or another FTP daemon) exposes a controlled directory so the Pi can pull or push without interaction.
* Credentials and directory mappings live in `/etc/pilink.yaml`.
* All transfers happen via Python’s `ftplib` (in `pilink/ftp_client.py`). Optionally swap to `lftp` or `curlftpfs` if you prefer shell tooling — the orchestrator abstracts this away.

### Storage layout

```
/data/
  pc_inbox/        # Files pulled from the computer before copying to the flash drive
  flash_outbox/    # Files staged from the flash drive before pushing to the computer
  logs/            # Consolidated application logs
/mnt/flash/        # USB flash drive, mounted via udev rule
```

### Software layers

* `pilink.config` – loads YAML config into typed dataclasses and exposes helper accessors.
* `pilink.ftp_client.FTPClient` – wraps Python’s `ftplib` to download/upload recursive directories with progress callbacks.
* `pilink.storage` – handles mounting checks, disk space validation, and checksum generation.
* `pilink.transfer_manager.TransferManager` – orchestrates the high-level flows (Computer → Flash, Flash → Computer) using the FTP client + storage helpers.
* `pilink.services.usb_watcher.USBMirrorService` – monitors `/data/pc_inbox` for new items and mirrors them automatically to `/mnt/flash`.
* `pilink.ui.app.PiLinkApp` – Textual-based TUI that provides the blue BIOS-style experience, status panels, logs, and action buttons.

### Services & boot flow

1. A `systemd` service called `pilink-ui.service` auto-logs in on `tty1` and runs `python -m pilink.ui.app`.
2. Another service `pilink-usb-watcher.service` starts after the USB storage mounts and keeps `/mnt/flash` synchronized.
3. Logging flows to `/var/log/pilink.log` using Python’s `logging` module with rotation.

Data flow diagrams
------------------

### Scenario 1 – Computer → Flash drive

1. User selects “Computer → Flash” on the UI.
2. `TransferManager.run_pc_to_flash()`:
   * Connect to the PC FTP server, mirror configured remote folder → `/data/pc_inbox/<timestamp>`.
   * Validate disk space on Pi and flash drive.
3. `USBMirrorService` copies the new folder to `/mnt/flash/transfers/<timestamp>` and computes checksums.
4. UI displays completion status; optional cleanup removes old staging data based on retention policy.

### Scenario 2 – Flash drive → Computer

1. User selects “Flash → Computer” and picks files/folders from the flash drive tree shown in the UI.
2. `TransferManager.run_flash_to_pc()`:
   * Copies selected items to `/data/flash_outbox/<timestamp>` (so FTP has a stable source).
   * Pushes the folder to the PC via FTP (reverse mirror).
3. UI streamlines status, showing throughput, ETA, and the PC target folder.

Security considerations
-----------------------

* Because FTP is plaintext, keep the link physically isolated or wrap inside an SSH tunnel if the cable touches anything else.
* Use non-guessable FTP credentials stored in `/etc/pilink.yaml` with root-only permissions.
* The PC FTP server should only expose a staging directory and enforce IP restrictions.
* Consider enabling FTPS in both directions if you need on-the-wire encryption; `FTPClient` is written so it can later use `ftplib.FTP_TLS`.

Extensibility
-------------

* Swap to SFTP by implementing `pilink/transport/base.py` and injecting a new transport into `TransferManager`.
* Add checksum comparison screens in the UI to confirm parity before deleting staging data.
* Connect to additional storage (NAS, cloud) by adding new menu items that call into `TransferManager`.

