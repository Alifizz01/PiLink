# PiLink Project Summary
## Complete Framework Overview

This document provides an overview of the entire PiLink project structure, what each component does, and how everything works together.

---

## Project Structure

```
PiLink/
├── README.md                          # Main project readme
├── PROJECT_SUMMARY.md                 # This file - project overview
├── requirements.txt                   # Python dependencies
│
├── config/                            # Configuration files
│   └── pilink.example.yaml           # Configuration template
│
├── docs/                              # Complete documentation
│   ├── INDEX.md                      # Documentation index/navigation
│   ├── QUICK_START.md                # 15-minute setup guide
│   ├── USER_GUIDE.md                 # Complete user manual
│   ├── INSTALLATION_CHECKLIST.md     # Step-by-step checklist
│   ├── TROUBLESHOOTING.md            # Problem solving guide
│   ├── architecture.md               # System architecture
│   ├── networking.md                 # Network configuration
│   └── operations.md                 # Operational procedures
│
├── scripts/                           # Setup and utility scripts
│   └── setup_pi.sh                   # Automated Pi setup script
│
├── services/                          # System services
│   ├── systemd/                      # Systemd service files
│   │   ├── pilink-ui.service         # UI auto-start service
│   │   └── pilink-usb-watcher.service # USB monitoring service
│   └── udev/                         # USB device rules
│       └── 99-pilink-flash.rules     # Auto-mount USB flash drive
│
└── src/                               # Application source code
    └── pilink/                       # Main Python package
        ├── __init__.py               # Package initialization
        ├── config.py                 # Configuration loader
        ├── ftp_client.py             # FTP client implementation
        ├── logging_utils.py          # Logging utilities
        ├── storage.py                # Storage/checksum utilities
        ├── transfer_manager.py       # Transfer orchestration
        ├── ui/                       # User interface
        │   ├── __init__.py
        │   ├── app.py                # Main UI application
        │   └── screens.py            # UI screen definitions
        └── services/                 # Background services
            └── usb_watcher.py        # USB flash drive watcher
```

---

## Component Overview

### Core Application (`src/pilink/`)

#### `config.py`
- Loads and validates YAML configuration
- Provides configuration access throughout application
- Handles configuration errors gracefully

#### `ftp_client.py`
- FTP client wrapper using `ftplib`
- Handles connections, transfers, and errors
- Supports both download and upload operations
- Implements retry logic and progress tracking

#### `storage.py`
- File system utilities
- Checksum generation and verification (SHA-256)
- Disk space checking
- File operations (copy, move, delete)

#### `transfer_manager.py`
- Orchestrates transfer operations
- Manages transfer workflows:
  - Computer → Flash Drive
  - Flash Drive → Computer
- Handles staging areas
- Coordinates FTP and local file operations
- Implements cleanup and retention policies

#### `logging_utils.py`
- Centralized logging configuration
- Log file rotation
- Structured log messages
- Error tracking

### User Interface (`src/pilink/ui/`)

#### `app.py`
- Main Textual application
- Screen management
- Event handling
- Status updates
- Integration with transfer manager

#### `screens.py`
- UI screen definitions:
  - Main menu screen
  - Transfer progress screens
  - Status displays
  - Log viewers
- Blue-screen UEFI-style theme
- Keyboard navigation

### Background Services (`src/pilink/services/`)

#### `usb_watcher.py`
- Monitors `/data/pc_inbox` for new files
- Automatically copies files to flash drive
- Uses `watchdog` library for file system events
- Handles flash drive mount/unmount
- Generates checksums
- Error recovery

### System Integration (`services/`)

#### `systemd/pilink-ui.service`
- Auto-starts UI on boot
- Runs on `tty1` (console)
- Full-screen interface
- Automatic restart on failure

#### `systemd/pilink-usb-watcher.service`
- Background service for USB monitoring
- Starts automatically
- Runs independently of UI
- Handles USB events

#### `udev/99-pilink-flash.rules`
- Automatically mounts USB flash drive
- Ensures consistent mount point (`/mnt/flash`)
- Triggers on USB device insertion

### Setup & Configuration

#### `scripts/setup_pi.sh`
- Automated installation script
- Installs system packages
- Sets up Python environment
- Configures services
- Installs udev rules
- One-command setup

#### `config/pilink.example.yaml`
- Configuration template
- All settings documented
- Copy to `/etc/pilink.yaml` and customize

---

## How It Works

### System Flow

1. **Boot Sequence:**
   - Raspberry Pi boots
   - Systemd starts `pilink-usb-watcher.service`
   - Systemd starts `pilink-ui.service` on `tty1`
   - UI displays blue-screen interface

2. **USB Flash Drive:**
   - USB device inserted
   - Udev rule triggers
   - Flash drive mounts at `/mnt/flash`
   - USB watcher monitors for files

3. **Transfer: Computer → Flash Drive:**
   - User selects "Computer → Flash" in UI
   - Transfer manager connects to PC FTP server
   - Downloads files to `/data/pc_inbox/<timestamp>`
   - USB watcher detects new files
   - Automatically copies to `/mnt/flash/transfers/<timestamp>`
   - Generates checksums
   - UI shows progress

4. **Transfer: Flash Drive → Computer:**
   - User selects "Flash → Computer" in UI
   - User browses and selects files from flash drive
   - Files copied to `/data/flash_outbox/<timestamp>`
   - Transfer manager connects to PC FTP server
   - Uploads files to PC
   - Verifies transfer
   - UI shows progress

### Data Flow

```
Computer → Flash Drive:
PC (FTP) → Pi (/data/pc_inbox) → Flash Drive (/mnt/flash/transfers)

Flash Drive → Computer:
Flash Drive (/mnt/flash) → Pi (/data/flash_outbox) → PC (FTP)
```

---

## Key Features

### Automated Operations
- ✅ Automatic USB flash drive mounting
- ✅ Automatic file copying to flash drive
- ✅ Automatic service startup on boot
- ✅ Automatic cleanup of old files

### User Experience
- ✅ Blue-screen UEFI-style interface
- ✅ Full-screen display (no window manager needed)
- ✅ Keyboard-only navigation
- ✅ Real-time progress indicators
- ✅ Status monitoring

### Reliability
- ✅ Checksum verification (SHA-256)
- ✅ Error handling and recovery
- ✅ Retry logic for network operations
- ✅ Logging for troubleshooting
- ✅ Service auto-restart

### Security
- ✅ Configuration file permissions (600)
- ✅ FTP credentials in config (not hardcoded)
- ✅ Isolated network (direct Ethernet)
- ✅ User permissions for file operations

---

## Dependencies

### System Packages (installed by setup script)
- `python3` - Python runtime
- `python3-pip` - Python package manager
- `lftp` - FTP client (for testing)
- `vsftpd` - FTP server (optional, for Pi as server)
- `watchdog` - File system monitoring
- `git` - Version control (for cloning)

### Python Packages (requirements.txt)
- `textual` - Terminal UI framework
- `pyyaml` - YAML configuration parsing
- `watchdog` - File system events

---

## Configuration

All configuration is in `/etc/pilink.yaml`:

- **UI settings** - Theme, log display
- **Paths** - Staging directories, mount points
- **PC endpoints** - FTP server connection details
- **Pi FTP** - Optional FTP server on Pi
- **USB watcher** - Monitoring settings
- **Logging** - Log levels and file locations
- **Alerts** - Optional GPIO/sound alerts

---

## Usage Workflows

### Initial Setup
1. Configure PC static IP and FileZilla Server
2. Configure Pi static IP
3. Run `setup_pi.sh` on Pi
4. Edit `/etc/pilink.yaml`
5. Reboot Pi

### Daily Operation
1. Power on Pi
2. UI appears automatically
3. Select transfer mode
4. Monitor progress
5. Files transfer automatically

### Maintenance
- View logs: `sudo tail -f /var/log/pilink.log`
- Restart services: `sudo systemctl restart pilink-ui.service`
- Clean staging: Press `P` in UI or run cleanup command
- Update: Pull latest code and restart services

---

## Documentation Guide

### For First-Time Users
1. Read [QUICK_START.md](docs/QUICK_START.md) for overview
2. Follow [USER_GUIDE.md](docs/USER_GUIDE.md) for detailed setup
3. Use [INSTALLATION_CHECKLIST.md](docs/INSTALLATION_CHECKLIST.md) to verify

### For Understanding System
1. Read [architecture.md](docs/architecture.md) for design
2. Review [networking.md](docs/networking.md) for network setup
3. Check [operations.md](docs/operations.md) for workflows

### For Problem Solving
1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
2. Review relevant section in [USER_GUIDE.md](docs/USER_GUIDE.md)
3. Check logs and service status

### Navigation
- Use [INDEX.md](docs/INDEX.md) to find the right documentation
- All docs are cross-referenced
- Each doc has a specific purpose

---

## Testing & Validation

### Pre-Deployment Testing
- [ ] FTP connection works both directions
- [ ] USB flash drive mounts automatically
- [ ] Services start on boot
- [ ] UI displays correctly
- [ ] Test transfers work

### Post-Deployment Testing
- [ ] Computer → Flash transfer completes
- [ ] Flash → Computer transfer completes
- [ ] Files are not corrupted (checksums match)
- [ ] Automatic cleanup works
- [ ] Error handling works (unplug flash drive, etc.)

---

## Future Enhancements (Potential)

- Web interface option
- Multiple PC endpoint support
- Transfer scheduling
- Email/SMS notifications
- Transfer history database
- Web-based configuration
- Multiple flash drive support
- Transfer encryption
- Bandwidth throttling
- Transfer queue management

---

## Support & Maintenance

### Logs Location
- Application: `/var/log/pilink.log`
- Systemd: `journalctl -u pilink-ui -u pilink-usb-watcher`

### Configuration Location
- Main config: `/etc/pilink.yaml`
- Backup: `/etc/pilink.yaml.backup` (create manually)

### Application Location
- Code: `/opt/pilink`
- Staging: `/data/pc_inbox`, `/data/flash_outbox`
- Flash mount: `/mnt/flash`

### Service Management
```bash
# Start/stop/restart
sudo systemctl start|stop|restart pilink-ui.service
sudo systemctl start|stop|restart pilink-usb-watcher.service

# Status
sudo systemctl status pilink-ui.service

# Enable/disable auto-start
sudo systemctl enable|disable pilink-ui.service
```

---

## Project Status

✅ **Complete Components:**
- Core application code
- User interface
- Background services
- System integration
- Setup scripts
- Complete documentation
- Configuration system

✅ **Ready for:**
- Installation and setup
- Testing on hardware
- Production deployment (after testing)

---

## Getting Started

1. **Read the documentation:**
   - Start with [docs/INDEX.md](docs/INDEX.md)
   - Follow [docs/QUICK_START.md](docs/QUICK_START.md)

2. **Set up hardware:**
   - Connect PC and Pi via Ethernet
   - Insert USB flash drive

3. **Install and configure:**
   - Follow [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
   - Use [docs/INSTALLATION_CHECKLIST.md](docs/INSTALLATION_CHECKLIST.md)

4. **Test and use:**
   - Perform test transfers
   - Verify everything works
   - Start using for real transfers

---

**Project Complete!** All code, documentation, and setup scripts are ready for deployment.

