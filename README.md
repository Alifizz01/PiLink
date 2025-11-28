PiLink – Raspberry Pi FTP Transfer Hub
======================================

PiLink turns a Raspberry Pi into a “blue screen” transfer appliance that sits between a Windows PC and a USB flash drive. It offers two automated workflows:

* Computer → Pi → Flash drive
* Flash drive → Pi → Computer

Both flows rely on FTP over a dedicated Ethernet link, so once the user makes a choice on the Pi UI, files move with zero extra interaction.

Documentation
-------------

**📚 [Documentation Index](docs/INDEX.md)** - Complete guide to all documentation

**Getting Started:**
- **[USER_GUIDE.md](docs/USER_GUIDE.md)** - Complete step-by-step setup and usage guide
- **[QUICK_START.md](docs/QUICK_START.md)** - Get running in 15 minutes
- **[INSTALLATION_CHECKLIST.md](docs/INSTALLATION_CHECKLIST.md)** - Step-by-step verification checklist

**Reference:**
- **[architecture.md](docs/architecture.md)** - System overview and component diagrams
- **[networking.md](docs/networking.md)** - Static IP + FTP guidance for PC <-> Pi
- **[operations.md](docs/operations.md)** - Runbooks, recovery steps, testing recipes
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common problems and solutions

Project contents
----------------

```
PiLink/
├── README.md
├── config/
│   └── pilink.example.yaml      # Sample configuration (copy to /etc/pilink.yaml)
├── docs/
│   ├── USER_GUIDE.md            # Complete setup and usage instructions
│   ├── QUICK_START.md            # Quick setup guide (15 minutes)
│   ├── architecture.md          # System overview and component diagrams
│   ├── networking.md            # Static IP + FTP guidance for PC <-> Pi
│   └── operations.md            # Runbooks, recovery steps, testing recipes
├── scripts/
│   └── setup_pi.sh              # Bootstrap script for a fresh Pi OS Lite install
├── services/
│   ├── systemd/
│   │   ├── pilink-ui.service            # boots directly into the blue-screen UI
│   │   └── pilink-usb-watcher.service   # mirrors staged files onto the flash drive
│   └── udev/
│       └── 99-pilink-flash.rules        # ensures the USB drive mounts at /mnt/flash
└── src/
    └── pilink/
        ├── __init__.py
        ├── config.py
        ├── ftp_client.py
        ├── logging_utils.py
        ├── storage.py
        ├── transfer_manager.py
        ├── ui/
        │   ├── __init__.py
        │   ├── app.py
        │   └── screens.py
        └── services/
            └── usb_watcher.py
```

Quick start
-----------

For detailed instructions, see [USER_GUIDE.md](docs/USER_GUIDE.md) or [QUICK_START.md](docs/QUICK_START.md).

**TL;DR:**
1. Configure static IPs on PC (`192.168.50.1`) and Pi (`192.168.50.2`)
2. Install FileZilla Server on PC and create FTP user
3. Run `sudo ./scripts/setup_pi.sh` on the Pi
4. Edit `/etc/pilink.yaml` with your FTP credentials
5. Reboot - PiLink UI starts automatically!

License
-------

This repository currently ships without a license file. Add the license that best matches your deployment needs (MIT, Apache-2.0, etc.) before distributing PiLink.

