# PiLink Troubleshooting Guide
## Common Issues and Solutions

This guide covers the most common problems and their solutions. For detailed setup instructions, see [USER_GUIDE.md](USER_GUIDE.md).

---

## Table of Contents

1. [Network Connectivity Issues](#network-connectivity-issues)
2. [FTP Connection Problems](#ftp-connection-problems)
3. [USB Flash Drive Issues](#usb-flash-drive-issues)
4. [UI/Service Problems](#uiservice-problems)
5. [Transfer Failures](#transfer-failures)
6. [Performance Issues](#performance-issues)
7. [Configuration Errors](#configuration-errors)

---

## Network Connectivity Issues

### Problem: Cannot ping between PC and Pi

**Symptoms:**
- `ping 192.168.50.1` fails from Pi
- `ping 192.168.50.2` fails from PC
- UI shows "PC Offline"

**Diagnosis:**
```bash
# On Pi
ip addr show eth0
ping 192.168.50.1

# On PC (Command Prompt)
ipconfig
ping 192.168.50.2
```

**Solutions:**

1. **Check Ethernet cable:**
   - Ensure cable is securely connected
   - Try a different cable
   - Check for physical damage

2. **Verify static IP configuration:**
   - **Pi:** Check `/etc/dhcpcd.conf`:
     ```bash
     cat /etc/dhcpcd.conf | grep -A 3 "interface eth0"
     ```
     Should show:
     ```
     interface eth0
     static ip_address=192.168.50.2/24
     static routers=192.168.50.1
     ```
   
   - **PC:** Check Network Adapter Settings:
     - IP: `192.168.50.1`
     - Subnet: `255.255.255.0`
     - Gateway: (blank)

3. **Restart network services:**
   ```bash
   # On Pi
   sudo systemctl restart dhcpcd
   
   # On PC
   # Disable and re-enable Ethernet adapter in Network Settings
   ```

4. **Check for IP conflicts:**
   - Ensure no other device uses `192.168.50.1` or `192.168.50.2`
   - Try different IP range (e.g., `192.168.51.x`)

5. **Verify adapter is active:**
   ```bash
   # On Pi
   ip link show eth0
   # Should show "state UP"
   ```

---

## FTP Connection Problems

### Problem: FTP login fails

**Symptoms:**
- "FTP authentication failed" error
- Cannot connect to FTP server
- UI shows "PC Offline" even though ping works

**Diagnosis:**
```bash
# Test FTP connection
lftp -u pilink,password -e "ls; quit" 192.168.50.1
```

**Solutions:**

1. **Verify FileZilla Server is running:**
   - Open FileZilla Server Interface on PC
   - Check status shows "Server online"
   - If not, start the service

2. **Check credentials:**
   ```bash
   # Verify config
   sudo cat /etc/pilink.yaml | grep -A 5 "pc_endpoints"
   ```
   - Username matches FileZilla Server user
   - Password is correct
   - No extra spaces or special characters

3. **Verify user permissions:**
   - In FileZilla Server Interface: Edit → Users
   - User `pilink` exists
   - Shared folders have Read + Write permissions
   - Paths are correct

4. **Check firewall:**
   - Windows Firewall allows port 21
   - Antivirus not blocking FTP
   - Test with firewall temporarily disabled

5. **Verify server binding:**
   - FileZilla Server → Edit → Settings → General settings
   - "Listen on these IP addresses" includes `192.168.50.1`
   - Port is `21`

6. **Test with different FTP client:**
   ```bash
   # On Pi, try with ftp command
   ftp 192.168.50.1
   # Enter username and password when prompted
   ```

### Problem: FTP connection times out

**Symptoms:**
- Connection hangs
- "Connection timed out" error
- Transfer starts but never completes

**Solutions:**

1. **Check network stability:**
   ```bash
   # Continuous ping test
   ping -c 100 192.168.50.1
   # Check for packet loss
   ```

2. **Increase timeout in config:**
   ```yaml
   # In /etc/pilink.yaml, add to pc_endpoints:
   timeout: 60
   ```

3. **Check FileZilla Server settings:**
   - Edit → Settings → Timeouts
   - Increase "No transfer timeout" to 600 seconds

4. **Verify cable quality:**
   - Use Cat5e or better Ethernet cable
   - Check cable length (should be < 100m)

---

## USB Flash Drive Issues

### Problem: Flash drive not detected

**Symptoms:**
- UI shows "Flash drive: Not mounted"
- Cannot access `/mnt/flash`
- USB watcher service errors

**Diagnosis:**
```bash
# Check if device is recognized
lsblk

# Check mount status
mount | grep flash

# Check dmesg for USB events
dmesg | tail -20
```

**Solutions:**

1. **Check USB device recognition:**
   ```bash
   lsblk
   # Should show device like /dev/sda1
   ```

2. **Manually mount (if needed):**
   ```bash
   # Find device
   sudo fdisk -l | grep -i "usb\|flash"
   
   # Mount (replace sda1 with your device)
   sudo mount /dev/sda1 /mnt/flash
   
   # Check permissions
   ls -la /mnt/flash
   ```

3. **Check udev rule:**
   ```bash
   # Verify rule exists
   cat /etc/udev/rules.d/99-pilink-flash.rules
   
   # Reload rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. **Check filesystem:**
   ```bash
   # Check if filesystem is supported
   sudo blkid /dev/sda1
   
   # If NTFS, may need ntfs-3g
   sudo apt install ntfs-3g
   ```

5. **Verify mount point permissions:**
   ```bash
   sudo chmod 755 /mnt/flash
   sudo chown root:root /mnt/flash
   ```

6. **Check USB power:**
   - Some flash drives need more power
   - Try powered USB hub
   - Try different USB port on Pi

### Problem: Cannot write to flash drive

**Symptoms:**
- Files copy but then disappear
- "Permission denied" errors
- USB watcher fails to copy files

**Solutions:**

1. **Check filesystem permissions:**
   ```bash
   # Check mount options
   mount | grep flash
   # Should not show "ro" (read-only)
   ```

2. **Check filesystem type:**
   ```bash
   sudo blkid /dev/sda1
   # FAT32/exFAT should work, NTFS may need ntfs-3g
   ```

3. **Remount with write permissions:**
   ```bash
   sudo umount /mnt/flash
   sudo mount -o rw,uid=pi,gid=pi /dev/sda1 /mnt/flash
   ```

4. **Check disk space:**
   ```bash
   df -h /mnt/flash
   ```

5. **Check for filesystem errors:**
   ```bash
   # For FAT32/exFAT (unmount first!)
   sudo umount /mnt/flash
   sudo fsck.vfat /dev/sda1
   sudo mount /dev/sda1 /mnt/flash
   ```

---

## UI/Service Problems

### Problem: UI doesn't start on boot

**Symptoms:**
- Pi boots to login prompt instead of UI
- No blue screen interface
- Service shows as failed

**Diagnosis:**
```bash
# Check service status
sudo systemctl status pilink-ui.service

# Check if enabled
sudo systemctl is-enabled pilink-ui.service

# View logs
sudo journalctl -u pilink-ui -n 50
```

**Solutions:**

1. **Verify service is enabled:**
   ```bash
   sudo systemctl enable pilink-ui.service
   ```

2. **Check service file:**
   ```bash
   cat /etc/systemd/system/pilink-ui.service
   # Verify paths are correct
   ```

3. **Check Python installation:**
   ```bash
   python3 --version
   which python3
   ```

4. **Check application path:**
   ```bash
   ls -la /opt/pilink/src/pilink/ui/app.py
   # Verify file exists
   ```

5. **Test manual start:**
   ```bash
   python3 -m pilink.ui.app --config /etc/pilink.yaml
   # Check for error messages
   ```

6. **Check dependencies:**
   ```bash
   pip3 list | grep textual
   # Should show textual package
   ```

7. **Check configuration:**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('/etc/pilink.yaml'))"
   # Should not show errors
   ```

### Problem: UI crashes or freezes

**Symptoms:**
- UI becomes unresponsive
- Error messages appear
- System becomes slow

**Solutions:**

1. **Check system resources:**
   ```bash
   # Check memory
   free -h
   
   # Check CPU
   top
   
   # Check disk space
   df -h
   ```

2. **Restart service:**
   ```bash
   sudo systemctl restart pilink-ui.service
   ```

3. **Check logs:**
   ```bash
   sudo tail -f /var/log/pilink.log
   # Look for error patterns
   ```

4. **Clear old logs:**
   ```bash
   sudo truncate -s 0 /var/log/pilink.log
   ```

5. **Check for Python errors:**
   ```bash
   python3 -m pilink.ui.app --config /etc/pilink.yaml 2>&1 | tee /tmp/pilink-debug.log
   ```

---

## Transfer Failures

### Problem: Transfer starts but fails mid-way

**Symptoms:**
- Progress bar stops
- Error message appears
- Files partially transferred

**Diagnosis:**
```bash
# Check logs
sudo tail -f /var/log/pilink.log

# Check disk space
df -h /data
df -h /mnt/flash
```

**Solutions:**

1. **Check disk space:**
   ```bash
   df -h
   # Ensure at least 10% free space
   ```

2. **Check file permissions:**
   ```bash
   ls -la /data/pc_inbox
   ls -la /mnt/flash
   ```

3. **Verify network stability:**
   ```bash
   # Monitor ping during transfer
   ping -c 100 192.168.50.1
   ```

4. **Check FTP server:**
   - FileZilla Server queue not paused
   - No connection limits reached
   - Server has enough resources

5. **Clear staging area:**
   ```bash
   # Remove old files
   sudo rm -rf /data/pc_inbox/*
   sudo rm -rf /data/flash_outbox/*
   ```

6. **Retry transfer:**
   - Cancel current transfer
   - Wait 30 seconds
   - Start new transfer

### Problem: Files transfer but are corrupted

**Symptoms:**
- Files appear on destination
- Files cannot be opened
- Checksum verification fails

**Solutions:**

1. **Verify checksums:**
   ```bash
   # On source
   sha256sum file.txt
   
   # On destination
   sha256sum file.txt
   # Should match
   ```

2. **Check network stability:**
   - Use quality Ethernet cable
   - Avoid interference sources
   - Check for packet loss

3. **Test with small file first:**
   - Transfer 1MB file
   - Verify integrity
   - If works, try larger files

4. **Check filesystem:**
   ```bash
   # Check for filesystem errors
   sudo fsck /dev/sda1
   ```

---

## Performance Issues

### Problem: Transfers are very slow

**Symptoms:**
- Transfer speed < 1 MB/s
- Takes hours for small files
- System seems sluggish

**Solutions:**

1. **Check Ethernet speed:**
   ```bash
   # On Pi
   ethtool eth0
   # Should show "Speed: 1000Mb/s" or "100Mb/s"
   ```

2. **Check for other processes:**
   ```bash
   top
   # Look for CPU-intensive processes
   ```

3. **Increase FTP parallel connections:**
   ```yaml
   # In /etc/pilink.yaml, add to pc_endpoints:
   parallel_connections: 4
   ```

4. **Check disk I/O:**
   ```bash
   iostat -x 1
   # Check for high wait times
   ```

5. **Use faster flash drive:**
   - USB 3.0 drive in USB 3.0 port
   - Higher quality flash drive
   - Check drive speed rating

---

## Configuration Errors

### Problem: Configuration file errors

**Symptoms:**
- Service fails to start
- "Invalid configuration" errors
- YAML parsing errors

**Diagnosis:**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('/etc/pilink.yaml'))"
```

**Solutions:**

1. **Check YAML syntax:**
   - Use online YAML validator
   - Check indentation (spaces, not tabs)
   - Verify all quotes are matched

2. **Verify required fields:**
   ```bash
   # Check config structure
   python3 -c "
   import yaml
   from pilink.config import Config
   config = Config('/etc/pilink.yaml')
   print('Config valid!')
   "
   ```

3. **Restore from backup:**
   ```bash
   sudo cp /etc/pilink.yaml.backup /etc/pilink.yaml
   ```

4. **Use example config:**
   ```bash
   sudo cp /opt/pilink/config/pilink.example.yaml /etc/pilink.yaml
   # Then edit with your values
   ```

---

## Getting More Help

If none of these solutions work:

1. **Collect diagnostic information:**
   ```bash
   # System info
   uname -a
   python3 --version
   ip addr show
   df -h
   
   # Service status
   sudo systemctl status pilink-ui.service
   sudo systemctl status pilink-usb-watcher.service
   
   # Recent logs
   sudo journalctl -u pilink-ui -n 100
   sudo tail -100 /var/log/pilink.log
   ```

2. **Check documentation:**
   - [USER_GUIDE.md](USER_GUIDE.md) - Complete setup guide
   - [architecture.md](architecture.md) - System architecture
   - [operations.md](operations.md) - Operational procedures

3. **Review logs carefully:**
   - Look for error patterns
   - Check timestamps
   - Note what was happening when error occurred

---

**Last Updated:** See [USER_GUIDE.md](USER_GUIDE.md) for the most current information.

