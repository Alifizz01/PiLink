# Troubleshooting

Start with **`pilink doctor`** (or key **5** on the screen). Every failed check says what to
do; the table below covers the same ground with a little more detail. Logs are in
`/data/logs/pilink.log` and `journalctl -u pilink-ui`.

## The PC

| PiLink says | Cause and fix |
|---|---|
| *refused the connection* | FileZilla Server is not running or not listening on that port. Start it; check *Server listeners*. |
| *No answer from 192.168.50.1:21* | Cable, IP or firewall. `ping 192.168.50.1` from the Pi. If ping works but FTP does not, allow `filezilla-server.exe` in Windows Firewall. |
| *No route to …* | The Pi has no address on the cable. `ip addr show eth0` should list `192.168.50.2`. Rerun `setup_pi.sh --static-ip 192.168.50.2/24`. |
| *rejected the username or password* | The user in FileZilla Server and `pc_endpoints` in `/etc/pilink.yaml` differ. |
| *The PC requires encrypted FTP* | FileZilla Server 1.x requires TLS by default: set `tls: true`. |
| *Encrypted FTP failed* | TLS is on in PiLink but not on the server, or the server certificate is broken: generate a new one in FileZilla Server, or set `tls: false` if TLS is off there. |
| *refused access to a folder* | The virtual path in `download_root` / `upload_root` does not exist for that user, or `/uploads` is not *Read+Write* with *Writable directory structure*. |
| Listing works, transfers hang | Passive mode is blocked: the firewall rule covers port 21 only. Allow the FileZilla Server program, or the passive port range from its settings. |

## The flash drive

| PiLink says | Cause and fix |
|---|---|
| *No flash drive* | Not mounted at `/mnt/flash`. `lsblk -f` should show the stick with a FAT/exFAT partition. Check `journalctl -b \| grep -i systemd-mount`. A stick without a partition table, or formatted with a filesystem Linux does not know, will not mount: format it FAT32 or exFAT. |
| *mounted read-only or not writable* | Usually an NTFS stick that Windows did not shut down cleanly, or an ext4 stick owned by root. Reformat as exFAT, or run `chkdsk` on Windows. |
| *Not enough space* | The numbers in the message are real: make room or use a bigger stick. Nothing has been copied yet when this appears. |
| *Verification failed for …* | The stick returned different bytes from what was written. Try another stick; this is what failing flash looks like. |
| *Could not unmount* | A shell or program on the Pi still has a file open on the stick (`lsof +f -- /mnt/flash`). The data is already flushed. |

## The screen

| Symptom | Fix |
|---|---|
| Black screen or a login prompt on tty1 | `systemctl status pilink-ui`. If it says the config is wrong, the message names the key: fix `/etc/pilink.yaml`. |
| Garbled characters | The console font lacks some symbols: `sudo dpkg-reconfigure console-setup`, choose UTF-8 and the *Terminus* font. |
| Need a login on the Pi's own screen | Alt+F2 opens a normal console (tty2); Alt+F1 goes back to PiLink. |

## After a failed transfer

Nothing is reported as copied until it has been verified, and every failure is in the history
(key **4**). The partly transferred files stay in `/data/pc_inbox` or `/data/flash_outbox` and
are cleaned up automatically after `retention_days`. Running the transfer again is always safe:
each run writes into a new dated folder and never overwrites a previous one.
