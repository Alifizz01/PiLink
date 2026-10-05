#!/usr/bin/env bash
# PiLink installer for Raspberry Pi OS (Bookworm or Bullseye).
#
#   sudo git clone https://github.com/Alifizz01/PiLink /opt/pilink
#   sudo /opt/pilink/scripts/setup_pi.sh                        # mode detected automatically
#   sudo /opt/pilink/scripts/setup_pi.sh --mode lite            # Pi OS Lite: full screen on the console
#   sudo /opt/pilink/scripts/setup_pi.sh --mode desktop         # Pi OS with desktop: a window + menu entry
#   sudo /opt/pilink/scripts/setup_pi.sh --static-ip 192.168.50.2/24 --user alif
#
# Safe to run again (also to switch modes): it updates the app and the system
# files, and never overwrites an existing /etc/pilink.yaml.
set -euo pipefail

APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG=/etc/pilink.yaml
USER_NAME="${SUDO_USER:-}"
STATIC_IP=""
IFACE=eth0
MODE=""
AUTOSTART=yes

log()  { printf '\033[1;34m[pilink]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[pilink] %s\033[0m\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)      USER_NAME="$2"; shift 2 ;;
    --static-ip) STATIC_IP="$2"; shift 2 ;;
    --iface)     IFACE="$2"; shift 2 ;;
    --mode)      MODE="$2"; shift 2 ;;
    --no-autostart) AUTOSTART=no; shift ;;
    -h|--help)   sed -n '2,12p' "$0"; exit 0 ;;
    *)           die "unknown option $1 (see --help)" ;;
  esac
done

[[ $EUID -eq 0 ]] || die "run with sudo"
# Raspberry Pi OS stopped shipping a default 'pi' user in 2022: use whoever ran sudo.
[[ -n "$USER_NAME" && "$USER_NAME" != root ]] || die "could not tell which user should run PiLink; pass --user NAME"
id "$USER_NAME" >/dev/null 2>&1 || die "user $USER_NAME does not exist"
USER_UID=$(id -u "$USER_NAME"); USER_GID=$(id -g "$USER_NAME")
USER_HOME=$(getent passwd "$USER_NAME" | cut -d: -f6)

if [[ -z "$MODE" ]]; then
  # A Pi that boots to a desktop has graphical.target as its default.
  if [[ "$(systemctl get-default 2>/dev/null)" == graphical.target ]]; then MODE=desktop; else MODE=lite; fi
  log "detected Raspberry Pi OS $([[ $MODE == desktop ]] && echo 'with desktop' || echo 'Lite') (override with --mode)"
fi
[[ "$MODE" == lite || "$MODE" == desktop ]] || die "--mode must be lite or desktop"

log "installing system packages"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git exfatprogs ntfs-3g >/dev/null

log "creating the app environment in $APP/.venv"
# Bookworm refuses system-wide pip installs (PEP 668), so PiLink gets its own venv.
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install -q --upgrade pip
"$APP/.venv/bin/pip" install -q "$APP"
chown -R "$USER_NAME:$USER_NAME" "$APP/.venv"

log "data folders under /data, owned by $USER_NAME"
install -d -o "$USER_NAME" -g "$USER_NAME" -m 0755 /data /data/pc_inbox /data/flash_outbox /data/logs
install -d -m 0755 /mnt/flash

if [[ -f $CONFIG ]]; then
  log "$CONFIG exists, keeping it"
else
  log "writing $CONFIG from the example (edit the PC endpoint next)"
  install -m 0640 -o root -g "$USER_NAME" "$APP/config/pilink.example.yaml" "$CONFIG"
  if [[ $MODE == desktop ]]; then
    # the desktop mounts sticks itself, under /media/<user>/<label>
    sed -i 's|^  flash_mount: .*|  flash_mount: "auto"                  # desktop: wherever the desktop mounts the stick|' "$CONFIG"
  fi
fi
# readable by the PiLink user (it holds the FTP password, so not by everyone)
chgrp "$USER_NAME" "$CONFIG"; chmod 0640 "$CONFIG"
if [[ $MODE == desktop ]] && ! grep -q 'flash_mount: *"\?auto' "$CONFIG"; then
  log "note: $CONFIG has a fixed flash_mount; for the desktop set   flash_mount: \"auto\""
fi

# the 2025 version installed this; it duplicated every copy, so it goes
if [[ -f /etc/systemd/system/pilink-usb-watcher.service ]]; then
  systemctl disable --now pilink-usb-watcher.service 2>/dev/null || true
  rm -f /etc/systemd/system/pilink-usb-watcher.service
fi

if [[ $MODE == lite ]]; then
  log "Lite mode: console UI on tty1, udev automount at /mnt/flash, sudoers entry for eject"
  sed -e "s|@USER@|$USER_NAME|g" -e "s|@APP@|$APP|g" "$APP/services/systemd/pilink-ui.service" \
    > /etc/systemd/system/pilink-ui.service
  sed -e "s|@UID@|$USER_UID|g" -e "s|@GID@|$USER_GID|g" "$APP/services/udev/99-pilink-flash.rules" \
    > /etc/udev/rules.d/99-pilink-flash.rules
  tmp=$(mktemp)
  sed -e "s|@USER@|$USER_NAME|g" "$APP/services/sudoers/pilink" > "$tmp"
  visudo -cf "$tmp" >/dev/null || die "generated sudoers entry failed validation; nothing installed"
  install -m 0440 "$tmp" /etc/sudoers.d/pilink && rm -f "$tmp"
  rm -f /usr/share/applications/pilink.desktop "$USER_HOME/.config/autostart/pilink.desktop"
  udevadm control --reload-rules
  systemctl daemon-reload
  # tty1 belongs to PiLink now; a login prompt is still on Alt+F2, and SSH is untouched
  systemctl disable getty@tty1.service >/dev/null 2>&1 || true
  systemctl enable pilink-ui.service >/dev/null
else
  log "Desktop mode: PiLink window + menu entry; the desktop mounts and ejects sticks"
  # nothing on the console, and no udev rule racing the desktop's own automounter
  if [[ -f /etc/systemd/system/pilink-ui.service ]]; then
    systemctl disable --now pilink-ui.service >/dev/null 2>&1 || true
    rm -f /etc/systemd/system/pilink-ui.service
    systemctl enable getty@tty1.service >/dev/null 2>&1 || true
  fi
  rm -f /etc/udev/rules.d/99-pilink-flash.rules /etc/sudoers.d/pilink
  udevadm control --reload-rules
  systemctl daemon-reload
  sed -e "s|@APP@|$APP|g" "$APP/services/desktop/pilink.desktop" > /usr/share/applications/pilink.desktop
  if [[ $AUTOSTART == yes ]]; then
    install -d -o "$USER_NAME" -g "$USER_NAME" "$USER_HOME/.config/autostart"
    install -m 0644 -o "$USER_NAME" -g "$USER_NAME" /usr/share/applications/pilink.desktop \
      "$USER_HOME/.config/autostart/pilink.desktop"
  else
    rm -f "$USER_HOME/.config/autostart/pilink.desktop"
  fi
  command -v lxterminal >/dev/null || log "note: lxterminal is missing; install it or edit the Exec line in pilink.desktop"
fi
ln -sf "$APP/.venv/bin/pilink" /usr/local/bin/pilink

if [[ -n "$STATIC_IP" ]]; then
  if command -v nmcli >/dev/null && systemctl is-active --quiet NetworkManager; then
    log "static IP $STATIC_IP on $IFACE (NetworkManager)"
    con=$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null || true)
    if [[ -z "$con" || "$con" == "--" ]]; then
      con="pilink-$IFACE"
      nmcli connection add type ethernet ifname "$IFACE" con-name "$con" >/dev/null
    fi
    nmcli connection modify "$con" ipv4.method manual ipv4.addresses "$STATIC_IP" ipv4.gateway "" ipv4.dns ""
    nmcli connection up "$con" >/dev/null || log "the address applies when the cable is connected"
  elif [[ -f /etc/dhcpcd.conf ]]; then
    log "static IP $STATIC_IP on $IFACE (dhcpcd)"
    sed -i '/# pilink-begin/,/# pilink-end/d' /etc/dhcpcd.conf
    printf '# pilink-begin\ninterface %s\nstatic ip_address=%s\n# pilink-end\n' "$IFACE" "$STATIC_IP" >> /etc/dhcpcd.conf
  else
    log "could not find NetworkManager or dhcpcd: set $STATIC_IP on $IFACE by hand"
  fi
fi

log "checking the installation"
sudo -u "$USER_NAME" "$APP/.venv/bin/pilink" --config "$CONFIG" doctor || true
if [[ $MODE == lite ]]; then
  START="sudo systemctl start pilink-ui   (or reboot: PiLink fills the screen)"
else
  START="open PiLink from the menu (Accessories), or log out and in: it starts automatically"
fi
cat <<EOF

PiLink is installed ($MODE mode).
  1. Edit the PC endpoint:   sudo nano $CONFIG
  2. Check everything:       pilink doctor
  3. Start it:               $START

EOF
