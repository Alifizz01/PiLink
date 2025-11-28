# PiLink Installation Checklist
## Step-by-Step Verification Guide

Use this checklist to ensure everything is configured correctly.

---

## Pre-Installation

### Hardware
- [ ] Raspberry Pi (3B+ or newer)
- [ ] MicroSD card (16GB+)
- [ ] USB flash drive (8GB+)
- [ ] Ethernet cable
- [ ] Power supply for Raspberry Pi
- [ ] Windows PC with Ethernet port

### Software Downloads
- [ ] Raspberry Pi Imager downloaded
- [ ] Raspberry Pi OS Lite image ready
- [ ] FileZilla Server installer downloaded

---

## PC Setup

### Network Configuration
- [ ] Opened Network Adapter Settings
- [ ] Configured static IP: `192.168.50.1`
- [ ] Subnet mask: `255.255.255.0`
- [ ] Gateway: (blank)
- [ ] DNS: (blank)
- [ ] Saved settings
- [ ] Verified IP with `ipconfig` command

### FileZilla Server Installation
- [ ] Installed FileZilla Server
- [ ] FileZilla Server Interface is running
- [ ] Created user: `pilink`
- [ ] Set password for `pilink` user
- [ ] Created shared folder: `C:\PiLinkShare`
- [ ] Set folder permissions: Read + Write
- [ ] Created subfolder: `downloads`
- [ ] Created subfolder: `uploads`
- [ ] Configured server to listen on `192.168.50.1`
- [ ] Port set to `21`
- [ ] Windows Firewall rule added for port 21

### Test PC Setup
- [ ] Can ping `192.168.50.1` from command prompt
- [ ] FileZilla Server shows "Server online" status

---

## Raspberry Pi Setup

### OS Installation
- [ ] Flashed Raspberry Pi OS Lite to MicroSD card
- [ ] Enabled SSH in Raspberry Pi Imager
- [ ] Set username and password
- [ ] Inserted MicroSD card into Pi
- [ ] Connected Ethernet cable (PC to Pi)
- [ ] Connected power supply
- [ ] Pi boots successfully

### Initial Pi Configuration
- [ ] Can SSH into Pi: `ssh pi@raspberrypi.local` (or via IP)
- [ ] Updated system: `sudo apt update && sudo apt upgrade -y`
- [ ] Changed default password (if needed)

### Network Configuration (Pi)
- [ ] Edited `/etc/dhcpcd.conf`
- [ ] Added static IP configuration:
  ```
  interface eth0
  static ip_address=192.168.50.2/24
  static routers=192.168.50.1
  ```
- [ ] Rebooted Pi: `sudo reboot`
- [ ] Verified static IP: `ip addr show eth0` shows `192.168.50.2`
- [ ] Can ping PC: `ping 192.168.50.1` (should work)

### PiLink Installation
- [ ] Cloned/copied PiLink to `/opt/pilink`
- [ ] Made setup script executable: `chmod +x scripts/setup_pi.sh`
- [ ] Ran setup script: `sudo ./scripts/setup_pi.sh`
- [ ] Setup completed without errors
- [ ] Python packages installed: `pip3 list | grep textual`

### Configuration
- [ ] Copied config template: `sudo cp config/pilink.example.yaml /etc/pilink.yaml`
- [ ] Edited `/etc/pilink.yaml`:
  - [ ] Updated PC host IP: `192.168.50.1`
  - [ ] Updated FTP username: `pilink`
  - [ ] Updated FTP password
  - [ ] Verified download_root: `/downloads`
  - [ ] Verified upload_root: `/uploads`
- [ ] Created required directories:
  ```bash
  sudo mkdir -p /data/pc_inbox /data/flash_outbox /data/logs /mnt/flash
  sudo chown -R pi:pi /data
  ```

### Service Installation
- [ ] Systemd services installed:
  - [ ] `/etc/systemd/system/pilink-ui.service` exists
  - [ ] `/etc/systemd/system/pilink-usb-watcher.service` exists
- [ ] Udev rule installed:
  - [ ] `/etc/udev/rules.d/99-pilink-flash.rules` exists
- [ ] Services enabled:
  - [ ] `sudo systemctl enable pilink-ui.service`
  - [ ] `sudo systemctl enable pilink-usb-watcher.service`

---

## Testing & Verification

### FTP Connection Test
- [ ] Tested FTP from Pi to PC:
  ```bash
  lftp -u pilink,password -e "ls; quit" 192.168.50.1
  ```
- [ ] FTP connection successful
- [ ] Can see directory listing

### USB Flash Drive Test
- [ ] Inserted USB flash drive into Pi
- [ ] Checked device: `lsblk` shows USB device
- [ ] Device mounts automatically (or manually: `sudo mount /dev/sda1 /mnt/flash`)
- [ ] Can access: `ls /mnt/flash`
- [ ] Has write permissions: `touch /mnt/flash/test.txt && rm /mnt/flash/test.txt`

### Service Status Check
- [ ] USB watcher service running:
  ```bash
  sudo systemctl status pilink-usb-watcher.service
  ```
- [ ] UI service can start:
  ```bash
  sudo systemctl start pilink-ui.service
  sudo systemctl status pilink-ui.service
  ```

### First Boot Test
- [ ] Rebooted Pi: `sudo reboot`
- [ ] After reboot, PiLink UI appears automatically
- [ ] UI shows status information:
  - [ ] Flash drive status visible
  - [ ] PC connection status visible
- [ ] Can navigate menu with arrow keys
- [ ] Can select menu options

---

## First Transfer Test

### Computer → Flash Test
- [ ] Created test file on PC: `C:\PiLinkShare\downloads\test.txt`
- [ ] Selected "1 - Computer → Flash" in PiLink UI
- [ ] Transfer started
- [ ] Progress displayed
- [ ] Transfer completed successfully
- [ ] Verified file on flash drive: `ls /mnt/flash/transfers/`
- [ ] File exists and is readable

### Flash → Computer Test
- [ ] Created test file on flash drive: `/mnt/flash/test_upload.txt`
- [ ] Selected "2 - Flash → Computer" in PiLink UI
- [ ] Selected test file
- [ ] Transfer started
- [ ] Progress displayed
- [ ] Transfer completed successfully
- [ ] Verified file on PC: `C:\PiLinkShare\uploads\`
- [ ] File exists and is readable

---

## Final Verification

### System Health
- [ ] Logs accessible: `sudo tail -f /var/log/pilink.log`
- [ ] No errors in logs
- [ ] Services auto-start on boot
- [ ] Flash drive auto-mounts when inserted
- [ ] USB watcher copies files automatically

### Documentation
- [ ] Read [USER_GUIDE.md](USER_GUIDE.md)
- [ ] Bookmarked troubleshooting section
- [ ] Know how to view logs
- [ ] Know how to restart services

---

## Troubleshooting Checklist

If something doesn't work, verify:

### Network Issues
- [ ] Both devices have correct static IPs
- [ ] Ethernet cable is connected
- [ ] Can ping between devices
- [ ] Firewall allows FTP (port 21)

### FTP Issues
- [ ] FileZilla Server is running
- [ ] Username/password correct in config
- [ ] Shared folders exist and have permissions
- [ ] Can connect via `lftp` command

### USB Issues
- [ ] Flash drive is recognized: `lsblk`
- [ ] Flash drive is mounted: `mount | grep flash`
- [ ] Has write permissions
- [ ] Enough free space

### Service Issues
- [ ] Services are enabled: `systemctl is-enabled pilink-ui`
- [ ] Services are running: `systemctl status pilink-ui`
- [ ] Check logs: `journalctl -u pilink-ui -n 50`
- [ ] Configuration file is valid: `python3 -c "import yaml; yaml.safe_load(open('/etc/pilink.yaml'))"`

---

## Installation Complete! ✅

If all items are checked, your PiLink system is ready to use!

**Next Steps:**
- Read the [USER_GUIDE.md](USER_GUIDE.md) for detailed usage instructions
- Perform regular transfers
- Monitor logs for any issues
- Keep system updated

---

**Date Completed:** _______________

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

