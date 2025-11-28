# PiLink Quick Start Guide
## Get Up and Running in 15 Minutes

This is a condensed guide. For detailed instructions, see [USER_GUIDE.md](USER_GUIDE.md).

---

## Prerequisites Checklist

- [ ] Raspberry Pi with Raspberry Pi OS Lite installed
- [ ] USB flash drive (8GB+)
- [ ] Ethernet cable (direct PC-to-Pi connection)
- [ ] Windows PC with Ethernet port
- [ ] FileZilla Server installed on PC

---

## Step 1: PC Setup (5 minutes)

### Configure Static IP
1. Control Panel → Network → Change adapter settings
2. Right-click Ethernet → Properties → IPv4
3. Set:
   - IP: `192.168.50.1`
   - Subnet: `255.255.255.0`
   - Gateway: (blank)

### Install & Configure FileZilla Server
1. Download and install FileZilla Server
2. Create user: `pilink` with password
3. Add shared folder: `C:\PiLinkShare` (read/write)
4. Create subfolders: `downloads` and `uploads`
5. Configure firewall to allow port 21

---

## Step 2: Raspberry Pi Setup (5 minutes)

### Configure Static IP
```bash
sudo nano /etc/dhcpcd.conf
```
Add at end:
```
interface eth0
static ip_address=192.168.50.2/24
static routers=192.168.50.1
```
Reboot: `sudo reboot`

### Install PiLink
```bash
cd /opt
sudo git clone <repo-url> pilink
cd pilink
sudo chmod +x scripts/setup_pi.sh
sudo ./scripts/setup_pi.sh
```

---

## Step 3: Configuration (3 minutes)

```bash
sudo nano /etc/pilink.yaml
```

Update:
- `pc_endpoints[0].host`: `192.168.50.1`
- `pc_endpoints[0].username`: `pilink`
- `pc_endpoints[0].password`: (your FileZilla password)
- `pc_endpoints[0].download_root`: `/downloads`
- `pc_endpoints[0].upload_root`: `/uploads`

Create directories:
```bash
sudo mkdir -p /data/pc_inbox /data/flash_outbox /data/logs /mnt/flash
sudo chown -R pi:pi /data
```

---

## Step 4: Test & Start (2 minutes)

### Test FTP Connection
```bash
lftp -u pilink,password -e "ls; quit" 192.168.50.1
```

### Reboot to Start
```bash
sudo reboot
```

After reboot, PiLink UI will start automatically!

---

## Using PiLink

### Main Menu Options
- **1** - Computer → Flash: Transfer PC files to flash drive
- **2** - Flash → Computer: Transfer flash drive files to PC
- **L** - View logs
- **Q** - Quit

### First Transfer Test

1. Place a test file in `C:\PiLinkShare\downloads` on your PC
2. On Pi, select **1 - Computer → Flash**
3. Watch the transfer progress
4. Check flash drive: files should be in `/mnt/flash/transfers/`

---

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| PC shows offline | Check IPs: `ip addr show eth0` (Pi) and `ipconfig` (PC) |
| Flash drive not found | Check: `lsblk` and `mount \| grep flash` |
| Transfer fails | Check logs: `sudo tail -f /var/log/pilink.log` |
| UI won't start | Check service: `sudo systemctl status pilink-ui.service` |

---

## Next Steps

- Read [USER_GUIDE.md](USER_GUIDE.md) for detailed instructions
- Review [architecture.md](architecture.md) for system overview
- Check [networking.md](networking.md) for network configuration details

---

**Need Help?** See the full [USER_GUIDE.md](USER_GUIDE.md) for comprehensive troubleshooting and maintenance instructions.

