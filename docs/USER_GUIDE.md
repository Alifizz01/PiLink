# PiLink User Guide
## Complete Setup and Usage Instructions

This guide walks you through installing, configuring, and using PiLink from start to finish.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Hardware Setup](#hardware-setup)
3. [PC Setup (Windows)](#pc-setup-windows)
4. [Raspberry Pi Setup](#raspberry-pi-setup)
5. [Configuration](#configuration)
6. [Starting PiLink](#starting-pilink)
7. [Using the Interface](#using-the-interface)
8. [Performing Transfers](#performing-transfers)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Prerequisites

### Hardware Required
- Raspberry Pi (3B+ or newer recommended)
- MicroSD card (16GB minimum, 32GB+ recommended)
- USB flash drive (8GB minimum)
- Ethernet cable (for direct PC-to-Pi connection)
- Power supply for Raspberry Pi
- Windows PC with Ethernet port

### Software Required
- Raspberry Pi OS Lite (64-bit recommended)
- FileZilla Server (for Windows PC)
- Python 3.8+ (comes with Raspberry Pi OS)
- Git (for cloning the repository)

---

## Hardware Setup

### Step 1: Connect Hardware

1. **Insert MicroSD card** into your Raspberry Pi
2. **Connect Ethernet cable** directly between your PC and Raspberry Pi (no router/switch needed)
3. **Insert USB flash drive** into Raspberry Pi USB port
4. **Connect power supply** to Raspberry Pi

**Important:** The Ethernet cable should connect ONLY your PC and Pi. Do not connect through a router or switch for the initial setup.

---

## PC Setup (Windows)

### Step 1: Configure Static IP Address

1. Open **Control Panel** → **Network and Sharing Center** → **Change adapter settings**
2. Right-click your **Ethernet adapter** → **Properties**
3. Select **Internet Protocol Version 4 (TCP/IPv4)** → **Properties**
4. Select **Use the following IP address:**
   - IP address: `192.168.50.1`
   - Subnet mask: `255.255.255.0`
   - Default gateway: (leave blank)
   - DNS servers: (leave blank)
5. Click **OK** to save

### Step 2: Install FileZilla Server

1. Download FileZilla Server from: https://filezilla-project.org/download.php?type=server
2. Install FileZilla Server with default settings
3. Launch **FileZilla Server Interface**

### Step 3: Configure FileZilla Server

1. In FileZilla Server Interface, click **Edit** → **Users**
2. Click **Add** to create a new user:
   - Username: `pilink`
   - Password: (choose a secure password, you'll need this later)
   - Click **OK**
3. In the **Shared folders** section:
   - Click **Add** under **Directories**
   - Browse to a folder where you want to share files (e.g., `C:\PiLinkShare`)
   - Set permissions: **Read** and **Write** (check both boxes)
   - Click **OK**
4. Click **OK** to save user settings
5. Click **Edit** → **Settings** → **General settings**
   - Listen on these IP addresses: `192.168.50.1`
   - Port: `21`
   - Click **OK**

### Step 4: Create Share Folders

Create these folders on your PC:
- `C:\PiLinkShare\downloads` - Files you want to transfer TO the flash drive
- `C:\PiLinkShare\uploads` - Destination for files FROM the flash drive

**Note:** Update FileZilla Server user permissions to include both folders with read/write access.

### Step 5: Configure Windows Firewall

1. Open **Windows Defender Firewall** → **Advanced settings**
2. Click **Inbound Rules** → **New Rule**
3. Select **Port** → **Next**
4. Select **TCP**, enter port `21` → **Next**
5. Select **Allow the connection** → **Next**
6. Check all profiles → **Next**
7. Name: "FileZilla FTP Server" → **Finish**

---

## Raspberry Pi Setup

### Step 1: Install Raspberry Pi OS

1. Download **Raspberry Pi Imager** from: https://www.raspberrypi.com/software/
2. Insert your MicroSD card into your computer
3. Open Raspberry Pi Imager:
   - Click **Choose OS** → **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (64-bit)**
   - Click **Choose Storage** → Select your MicroSD card
   - Click the gear icon (⚙️) to configure:
     - Enable SSH
     - Set username: `pi` (or your preferred username)
     - Set password: (choose a secure password)
     - Configure wireless LAN: (optional, not needed for Ethernet)
   - Click **Write** to flash the OS

### Step 2: Configure Static IP on Raspberry Pi

1. Boot the Raspberry Pi and connect via SSH:
   ```bash
   ssh pi@raspberrypi.local
   ```
   Or if that doesn't work, find the IP address from your router and connect:
   ```bash
   ssh pi@<pi-ip-address>
   ```

2. Edit the network configuration:
   ```bash
   sudo nano /etc/dhcpcd.conf
   ```

3. Add these lines at the end of the file:
   ```
   interface eth0
   static ip_address=192.168.50.2/24
   static routers=192.168.50.1
   ```

4. Save and exit (Ctrl+X, then Y, then Enter)

5. Reboot:
   ```bash
   sudo reboot
   ```

### Step 3: Install PiLink

1. After reboot, SSH back into the Pi

2. Clone the PiLink repository:
   ```bash
   cd /opt
   sudo git clone <your-repo-url> pilink
   ```
   Or if you have the files locally, copy them:
   ```bash
   sudo mkdir -p /opt/pilink
   # Copy all PiLink files to /opt/pilink
   ```

3. Run the setup script:
   ```bash
   cd /opt/pilink
   sudo chmod +x scripts/setup_pi.sh
   sudo ./scripts/setup_pi.sh
   ```

   This script will:
   - Install required system packages (Python, lftp, vsftpd, etc.)
   - Install Python dependencies
   - Copy configuration template
   - Install systemd services
   - Install udev rules for USB mounting

4. Wait for the setup to complete (may take 5-10 minutes)

---

## Configuration

### Step 1: Edit Configuration File

1. Open the configuration file:
   ```bash
   sudo nano /etc/pilink.yaml
   ```

2. Update the following sections:

   **PC FTP Connection:**
   ```yaml
   pc_endpoints:
     - name: "default_pc"
       host: "192.168.50.1"        # Your PC's IP address
       port: 21
       username: "pilink"          # FileZilla Server username
       password: "your-password"   # FileZilla Server password
       download_root: "/downloads" # Path on PC for files to transfer TO flash
       upload_root: "/uploads"     # Path on PC for files FROM flash
   ```

   **Paths (adjust if needed):**
   ```yaml
   paths:
     staging_root: "/data"
     pc_inbox: "/data/pc_inbox"
     flash_outbox: "/data/flash_outbox"
     flash_mount: "/mnt/flash"
     flash_transfer_root: "/mnt/flash/transfers"
   ```

   **USB Flash Drive:**
   ```yaml
   flash_drive:
     min_required_gb: 8  # Minimum flash drive size
   ```

3. Save and exit (Ctrl+X, then Y, then Enter)

### Step 2: Create Required Directories

```bash
sudo mkdir -p /data/pc_inbox /data/flash_outbox /data/logs /mnt/flash
sudo chown -R pi:pi /data
```

### Step 3: Test FTP Connection

Test that the Pi can connect to your PC:
```bash
lftp -u pilink,your-password -e "ls; quit" 192.168.50.1
```

You should see a directory listing. If not, check:
- PC firewall settings
- FileZilla Server is running
- IP addresses are correct
- Username/password are correct

---

## Starting PiLink

### Automatic Start (Recommended)

PiLink is configured to start automatically on boot. Simply reboot:
```bash
sudo reboot
```

After reboot, the PiLink blue-screen interface will appear automatically.

### Manual Start

If you need to start manually:

1. Start the USB watcher service:
   ```bash
   sudo systemctl start pilink-usb-watcher.service
   ```

2. Start the UI:
   ```bash
   python3 -m pilink.ui.app --config /etc/pilink.yaml
   ```

### Check Service Status

```bash
# Check if services are running
sudo systemctl status pilink-ui.service
sudo systemctl status pilink-usb-watcher.service

# View logs
sudo journalctl -u pilink-ui -f
sudo journalctl -u pilink-usb-watcher -f
```

---

## Using the Interface

### Main Menu

When PiLink starts, you'll see a blue-screen interface with:

- **Status Panel** (top):
  - Flash drive status (mounted, capacity, free space)
  - PC connection status (online/offline)
  - Last transfer information

- **Main Menu** (center):
  - `1` - **Computer → Flash**: Transfer files from PC to flash drive
  - `2` - **Flash → Computer**: Transfer files from flash drive to PC
  - `L` - **View Logs**: Display recent transfer logs
  - `P` - **Prune Staging**: Clean up old staging files
  - `Q` - **Quit**: Exit to shell

### Navigation

- Use **Arrow Keys** to navigate menus
- Press **Enter** to select
- Press **Esc** to go back
- Press **Q** to quit

---

## Performing Transfers

### Transfer Mode 1: Computer → Flash Drive

**Purpose:** Copy files from your PC to the USB flash drive via the Raspberry Pi.

**Steps:**

1. On the main menu, select **`1 - Computer → Flash`**

2. The system will:
   - Connect to your PC via FTP
   - List available files in the PC's download folder
   - Show transfer progress

3. Files are automatically:
   - Downloaded to `/data/pc_inbox/<timestamp>` on the Pi
   - Copied to `/mnt/flash/transfers/<timestamp>` on the flash drive
   - Verified with checksums

4. Monitor progress:
   - Transfer speed (MB/s)
   - Files transferred
   - Time remaining
   - Status messages

5. When complete:
   - You'll see a success message
   - Files are on the flash drive
   - Press **Esc** to return to main menu

**What happens behind the scenes:**
1. Pi connects to PC FTP server
2. Downloads all files from PC's `/downloads` folder
3. USB watcher automatically detects new files
4. Copies files to flash drive
5. Generates checksums for verification

### Transfer Mode 2: Flash Drive → Computer

**Purpose:** Copy files from the USB flash drive to your PC via the Raspberry Pi.

**Steps:**

1. On the main menu, select **`2 - Flash → Computer`**

2. Browse flash drive contents:
   - Use arrow keys to navigate
   - Press **Space** to select files/folders
   - Press **Enter** to confirm selection

3. Select destination on PC:
   - Choose from configured PC endpoints
   - Or specify a custom path

4. The system will:
   - Copy selected files to staging area
   - Upload to PC via FTP
   - Verify transfer with checksums

5. Monitor progress:
   - Upload speed
   - Files uploaded
   - Progress bar

6. When complete:
   - Success message appears
   - Files are on your PC
   - Press **Esc** to return to main menu

**What happens behind the scenes:**
1. Pi reads selected files from flash drive
2. Copies to `/data/flash_outbox/<timestamp>`
3. Connects to PC FTP server
4. Uploads files to PC's `/uploads` folder
5. Verifies transfer integrity

---

## Troubleshooting

### Problem: UI doesn't start on boot

**Solution:**
```bash
# Check service status
sudo systemctl status pilink-ui.service

# Check if service is enabled
sudo systemctl is-enabled pilink-ui.service

# Enable and start manually
sudo systemctl enable pilink-ui.service
sudo systemctl start pilink-ui.service

# Check logs
sudo journalctl -u pilink-ui -n 50
```

### Problem: "PC Offline" status

**Checklist:**
1. Verify Ethernet cable is connected
2. Check IP addresses:
   ```bash
   # On Pi
   ip addr show eth0
   # Should show 192.168.50.2
   
   # On PC
   ipconfig
   # Should show 192.168.50.1
   ```
3. Test connectivity:
   ```bash
   ping 192.168.50.1
   ```
4. Verify FileZilla Server is running on PC
5. Test FTP connection:
   ```bash
   lftp -u pilink,password -e "ls; quit" 192.168.50.1
   ```

### Problem: Flash drive not detected

**Solution:**
```bash
# Check if USB device is recognized
lsblk

# Check mount status
mount | grep flash

# Check udev rules
ls -la /etc/udev/rules.d/99-pilink-flash.rules

# Manually mount (if needed)
sudo mount /dev/sda1 /mnt/flash
```

### Problem: Transfer fails or hangs

**Solution:**
1. Check available space:
   ```bash
   df -h /data
   df -h /mnt/flash
   ```

2. Check logs:
   ```bash
   sudo tail -f /var/log/pilink.log
   ```

3. Verify FTP credentials in `/etc/pilink.yaml`

4. Restart services:
   ```bash
   sudo systemctl restart pilink-ui.service
   sudo systemctl restart pilink-usb-watcher.service
   ```

### Problem: Files not copying to flash drive

**Solution:**
1. Check USB watcher service:
   ```bash
   sudo systemctl status pilink-usb-watcher.service
   ```

2. Check if flash drive is mounted:
   ```bash
   mount | grep /mnt/flash
   ```

3. Check permissions:
   ```bash
   ls -la /mnt/flash
   sudo chmod 755 /mnt/flash
   ```

4. Manually trigger copy (for testing):
   ```bash
   sudo systemctl restart pilink-usb-watcher.service
   ```

### Problem: Can't connect via SSH after static IP

**Solution:**
1. Connect via HDMI/monitor and keyboard
2. Or connect via WiFi (if configured)
3. Or use router to find new IP address
4. Verify static IP configuration:
   ```bash
   cat /etc/dhcpcd.conf
   ```

---

## Maintenance

### Viewing Logs

**System logs:**
```bash
# PiLink application logs
sudo tail -f /var/log/pilink.log

# Service logs
sudo journalctl -u pilink-ui -f
sudo journalctl -u pilink-usb-watcher -f

# Combined logs
sudo journalctl -u pilink-ui -u pilink-usb-watcher -f
```

### Cleaning Up Old Files

**Automatic cleanup:**
- Old staging files are automatically deleted after the retention period (default: 7 days)
- Configure in `/etc/pilink.yaml`:
  ```yaml
  paths:
    retention_days: 7
  ```

**Manual cleanup:**
1. From UI: Press **P** on main menu
2. Or from command line:
   ```bash
   python3 -m pilink.transfer_manager --prune
   ```

### Updating PiLink

```bash
cd /opt/pilink
sudo git pull
sudo pip3 install -r requirements.txt --upgrade
sudo systemctl restart pilink-ui.service
sudo systemctl restart pilink-usb-watcher.service
```

### Safely Ejecting Flash Drive

1. From UI: Press **E** on main menu (if available)
2. Or from command line:
   ```bash
   sudo umount /mnt/flash
   ```

### Backup Configuration

```bash
# Backup config
sudo cp /etc/pilink.yaml /etc/pilink.yaml.backup

# Restore config
sudo cp /etc/pilink.yaml.backup /etc/pilink.yaml
```

### Resetting to Defaults

```bash
# Restore default config
sudo cp /opt/pilink/config/pilink.example.yaml /etc/pilink.yaml
sudo nano /etc/pilink.yaml  # Edit with your settings

# Restart services
sudo systemctl restart pilink-ui.service
sudo systemctl restart pilink-usb-watcher.service
```

---

## Quick Reference

### Important Commands

```bash
# Service management
sudo systemctl start pilink-ui.service
sudo systemctl stop pilink-ui.service
sudo systemctl restart pilink-ui.service
sudo systemctl status pilink-ui.service

# View logs
sudo journalctl -u pilink-ui -f
sudo tail -f /var/log/pilink.log

# Test FTP connection
lftp -u username,password -e "ls; quit" 192.168.50.1

# Check disk space
df -h

# Check USB devices
lsblk

# Manual mount (if needed)
sudo mount /dev/sda1 /mnt/flash
```

### Important File Locations

- Configuration: `/etc/pilink.yaml`
- Application logs: `/var/log/pilink.log`
- Staging area: `/data/pc_inbox`, `/data/flash_outbox`
- Flash drive mount: `/mnt/flash`
- Application code: `/opt/pilink`

### Default IP Addresses

- PC: `192.168.50.1`
- Raspberry Pi: `192.168.50.2`

---

## Support

If you encounter issues not covered in this guide:

1. Check the logs (see [Viewing Logs](#viewing-logs))
2. Review the troubleshooting section
3. Check the architecture documentation: `docs/architecture.md`
4. Review networking setup: `docs/networking.md`
5. Check operations guide: `docs/operations.md`

---

## Appendix: FileZilla Server Path Configuration

When configuring FileZilla Server, the paths you set in the user's "Shared folders" section should match:

- **Downloads folder** (PC → Flash): This is where you place files on your PC that you want to transfer to the flash drive
- **Uploads folder** (Flash → PC): This is where files from the flash drive will be saved on your PC

In `/etc/pilink.yaml`, these correspond to:
- `download_root`: Path relative to FileZilla user's root (e.g., `/downloads`)
- `upload_root`: Path relative to FileZilla user's root (e.g., `/uploads`)

**Example FileZilla Setup:**
- User root: `C:\PiLinkShare`
- Downloads: `C:\PiLinkShare\downloads` → Use `/downloads` in config
- Uploads: `C:\PiLinkShare\uploads` → Use `/uploads` in config

---

**End of User Guide**

