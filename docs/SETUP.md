# Setting up PiLink

About 20 minutes. You need a Raspberry Pi (3, 4 or 5) with Raspberry Pi OS (Bookworm or
Bullseye, Lite is enough), an Ethernet cable between the Pi and the Windows PC, a screen and
keyboard on the Pi, and a USB flash drive formatted **FAT32 or exFAT**.

```
 Windows PC                          Raspberry Pi                    USB flash drive
 192.168.50.1  ── Ethernet cable ──  192.168.50.2  ── USB port ──   mounted at /mnt/flash
 FileZilla Server                    PiLink on the screen (tty1)
```

## 1. The Windows PC

**Static IP on the cable.** Settings → Network & Internet → Ethernet → IP assignment → Edit →
Manual, IPv4 on: IP `192.168.50.1`, subnet prefix length `24`, no gateway, no DNS. Leave Wi‑Fi
alone; the PC keeps its internet connection.

**FileZilla Server** (free, [filezilla-project.org](https://filezilla-project.org/download.php?type=server)):

1. Install it and open the administration interface (it connects to the server on `localhost`).
2. *Server → Configure → Rights management → Users → Add*: name `pilink`, set a password.
3. In that user's *Mount points* add two folders, for example
   - virtual path `/computer_share` → native path `C:\PiLink\computer_share`, access **Read only**
   - virtual path `/uploads` → native path `C:\PiLink\uploads`, access **Read+Write**, and tick
     **Writable directory structure** (PiLink creates a dated subfolder for every upload)
4. *Server listeners*: port 21 on all addresses (the default).
5. FileZilla Server 1.x requires **explicit FTP over TLS** by default. That is fine: keep
   `tls: true` in PiLink's config. If you switch TLS off in FileZilla, set `tls: false`.
   (Older 0.9.x versions do not use TLS unless configured to: `tls: false`.)

**Windows Firewall.** FileZilla Server's installer usually adds the rule. If `pilink doctor`
says the PC does not answer: Windows Security → Firewall → *Allow an app* → allow
`filezilla-server.exe` on the network the cable is on. Passive-mode transfers use a port range
(*Server → Configure → Passive mode*); the app rule covers it, a port rule would have to
include that range too.

Put the files you want on the stick into `C:\PiLink\computer_share`.

## 2. The Raspberry Pi

PiLink runs on both editions of Raspberry Pi OS. The installer detects which one it is on;
`--mode` overrides that.

| | **Lite** (`--mode lite`) | **With desktop** (`--mode desktop`) |
|---|---|---|
| How PiLink appears | full screen on the console (tty1) from boot, like an appliance | a terminal window that opens when you log in, plus *Menu → Accessories → PiLink* |
| USB stick | PiLink's udev rule mounts it at `/mnt/flash` | the desktop mounts it as usual (`/media/<user>/<label>`); config has `flash_mount: "auto"` |
| Safely remove (key 3) | unmount through a sudoers entry that allows only that | `udisksctl`, exactly like the desktop's eject button |
| Login prompt on tty1 | moved to Alt+F2 | untouched |
| Best for | a dedicated transfer box, screen + keyboard only | a Pi that is also used as a normal computer |

```bash
sudo git clone https://github.com/Alifizz01/PiLink /opt/pilink
sudo /opt/pilink/scripts/setup_pi.sh --static-ip 192.168.50.2/24              # mode auto-detected
#   or explicitly:  ... setup_pi.sh --mode lite      |   ... setup_pi.sh --mode desktop
sudo nano /etc/pilink.yaml        # username, password and folders from step 1
pilink doctor                     # every check should say [ ok ]
sudo reboot                       # Lite: PiLink fills the screen. Desktop: it opens after login
```

Switching later is the same command with the other `--mode`; it removes what the old mode
installed. In desktop mode, `--no-autostart` keeps the menu entry but does not open PiLink at login.

What `setup_pi.sh` does, so nothing is a surprise:

| step | detail |
|---|---|
| packages | `python3-venv`, `git`, `exfatprogs`, `ntfs-3g` |
| app | a virtualenv in `/opt/pilink/.venv` (Bookworm blocks system-wide `pip`), `pilink` on the PATH |
| user | the user who ran `sudo` (or `--user NAME`); Raspberry Pi OS has no default `pi` user any more |
| folders | `/data/*` owned by that user |
| config | `/etc/pilink.yaml` from the example, readable by that user only (it holds the FTP password); desktop mode sets `flash_mount: "auto"` |
| Lite only | udev rule mounting the stick at `/mnt/flash` (owned by that user, `flush` on FAT); sudoers entry allowing only `umount /mnt/flash`; `pilink-ui.service` on tty1 |
| Desktop only | `/usr/share/applications/pilink.desktop` and the same file in `~/.config/autostart/` |
| network | `--static-ip` sets the address with NetworkManager (Bookworm) or dhcpcd (older images) |

Running it again updates everything and keeps your `/etc/pilink.yaml`. Updating later:

```bash
cd /opt/pilink && sudo git pull && sudo scripts/setup_pi.sh && sudo systemctl restart pilink-ui
```

## 3. Using it

| key | does |
|---|---|
| **1** | Computer → Flash drive: everything in the PC's `computer_share` folder is downloaded, written to the stick under `transfers/<date-time>/`, read back and compared against its checksums, with `checksums.txt` alongside |
| **2** | Flash drive → Computer: pick files and folders on the stick (**Space** selects, **A** the whole stick, **U** uploads); they arrive on the PC in `uploads/<date-time>/` with `checksums.txt`, and every file's size is checked on the PC |
| **3** | Safely remove the flash drive: everything is flushed and the stick is unmounted |
| **4** | History of every transfer, failed ones included |
| **5** | Diagnostics: the same checks as `pilink doctor` |

The same from SSH: `pilink status`, `pilink pc-to-flash`, `pilink flash-to-pc Measurements report.pdf`,
`pilink eject`, `pilink history`.

To check a stick on any Linux machine later: `cd transfers/<date-time> && sha256sum -c checksums.txt`.
On Windows: `certutil -hashfile FILE SHA256` and compare with the line in `checksums.txt`.
