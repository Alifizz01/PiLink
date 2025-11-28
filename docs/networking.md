Networking & FTP Setup
======================

Dedicated Ethernet link
-----------------------

1. Use a standard Ethernet cable between the PC NIC and the Pi’s Ethernet port (modern hardware supports auto-MDI/MDIX; crossover is unnecessary).
2. Assign static IPv4 addresses:

   * Windows PC: open *Network & Internet Settings → Change adapter options → Properties → IPv4* and set  
     `IP 192.168.50.1 / Mask 255.255.255.0 / Gateway blank / DNS blank`.
   * Raspberry Pi: edit `/etc/dhcpcd.conf` and append

     ```
     interface eth0
       static ip_address=192.168.50.2/24
       static routers=
       static domain_name_servers=
     ```

3. Reboot both devices or bounce the interfaces.
4. Test with `ping 192.168.50.2` from Windows and `ping 192.168.50.1` from the Pi.

FTP services
------------

### Windows (FileZilla Server example)

1. Install FileZilla Server.
2. Create a user `pilink` with a strong password and restrict it to a dedicated folder, e.g. `C:\PiLink\ftp_root`.
3. Assign read/write permissions depending on direction:
   * For Computer → Flash: grant *download* (the Pi pulls files).
   * For Flash → Computer: grant *upload* to a different folder (e.g. `C:\PiLink\uploads`).
4. Restrict IPs: Settings → IP filter → only allow `192.168.50.2`.
5. Optional: enable FTP over TLS and import a certificate.

### Raspberry Pi (vsftpd)

```
sudo apt update
sudo apt install vsftpd
sudo cp /etc/vsftpd.conf /etc/vsftpd.conf.bak
```

Key snippets for `/etc/vsftpd.conf`:

```
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
chroot_local_user=YES
allow_writeable_chroot=YES
pasv_enable=YES
pasv_min_port=50000
pasv_max_port=50010
```

Create a local account that owns `/data/vsftpd` and is limited to that folder.

Firewall rules (optional)
-------------------------

On the Pi (ufw):

```
sudo ufw allow from 192.168.50.1 to any port 21 proto tcp
sudo ufw allow from 192.168.50.1 to any port 50000:50010 proto tcp
```

On Windows, ensure the adapter is set to “Private network” and add inbound rules allowing FileZilla Server.

Testing checklist
-----------------

1. From the Pi: `ftp 192.168.50.1`, log in with the PC credentials, `ls`, and `get` a test file.
2. From Windows: `ftp 192.168.50.2`, log in with the Pi credentials, and `put` a file.
3. Confirm the staging directories on both machines change accordingly.
4. Update `config/pilink.yaml` with the verified IPs, usernames, passwords, and remote paths.

