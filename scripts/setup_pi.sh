#!/usr/bin/env bash
set -euo pipefail

# PiLink bootstrap script.
# Run on a fresh Raspberry Pi OS Lite install after cloning this repo to /opt/pilink.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DST="/etc/pilink.yaml"

log() {
  printf '[setup] %s\n' "$*" >&2
}

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root (sudo)." >&2
    exit 1
  fi
}

install_packages() {
  log "Updating apt cache..."
  apt-get update
  log "Installing system packages..."
  apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    lftp \
    vsftpd \
    watchdog \
    git
}

setup_python() {
  log "Installing Python requirements..."
  pip3 install --upgrade pip
  pip3 install -r "$REPO_DIR/requirements.txt"
}

install_config() {
  if [[ -f $CONFIG_DST ]]; then
    log "$CONFIG_DST exists, skipping copy."
  else
    log "Copying sample config to $CONFIG_DST"
    cp "$REPO_DIR/config/pilink.example.yaml" "$CONFIG_DST"
    chmod 600 "$CONFIG_DST"
  fi
}

install_services() {
  log "Installing systemd service units..."
  install -m 0644 "$REPO_DIR/services/systemd/pilink-ui.service" /etc/systemd/system/pilink-ui.service
  install -m 0644 "$REPO_DIR/services/systemd/pilink-usb-watcher.service" /etc/systemd/system/pilink-usb-watcher.service
  log "Installing udev rule..."
  install -m 0644 "$REPO_DIR/services/udev/99-pilink-flash.rules" /etc/udev/rules.d/99-pilink-flash.rules
  udevadm control --reload-rules
  log "Enabling services..."
  systemctl daemon-reload
  systemctl enable pilink-ui.service
  systemctl enable pilink-usb-watcher.service
}

main() {
  require_root
  install_packages
  setup_python
  install_config
  install_services
  log "Setup complete. Reboot to launch PiLink UI."
}

main "$@"

