"""Load and validate /etc/pilink.yaml.

Every problem is reported as a ConfigError that names the exact key, because
the person reading it is standing at a Pi with a keyboard, not a debugger.
"""
from __future__ import annotations

import dataclasses
import pathlib
from typing import Any

import yaml

DEFAULT_PATH = "/etc/pilink.yaml"


class ConfigError(ValueError):
    pass


@dataclasses.dataclass
class UIConfig:
    theme: str = "blue"
    log_lines: int = 200


@dataclasses.dataclass
class PathConfig:
    staging_root: str = "/data"
    pc_inbox: str = "/data/pc_inbox"
    flash_outbox: str = "/data/flash_outbox"
    log_dir: str = "/data/logs"
    flash_mount: str = "/mnt/flash"      # "auto" on Pi OS with desktop: wherever the desktop mounts the stick
    flash_transfer_root: str = "/mnt/flash/transfers"
    retention_days: int = 7
    # Refuse to write "to the flash drive" unless something is really mounted
    # there; otherwise the files silently land on the SD card. Only the demo
    # and the tests turn this off.
    require_mount: bool = True


@dataclasses.dataclass
class FlashConfig:
    # Folders on the stick the file picker never offers.
    hidden: tuple = ("System Volume Information", "$RECYCLE.BIN", ".Trashes", ".Spotlight-V100", ".fseventsd")
    min_required_gb: float = 0     # retired: free space is now checked against the actual transfer


@dataclasses.dataclass
class EndpointConfig:
    name: str
    host: str
    username: str
    password: str
    download_root: str = "/"
    upload_root: str = "/uploads"
    port: int = 21
    tls: bool = False          # explicit FTPS; FileZilla Server 1.x requires it by default
    timeout: int = 20


@dataclasses.dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "/data/logs/pilink.log"


@dataclasses.dataclass
class Config:
    paths: PathConfig
    pc_endpoints: list
    ui: UIConfig = dataclasses.field(default_factory=UIConfig)
    flash_drive: FlashConfig = dataclasses.field(default_factory=FlashConfig)
    logging: LoggingConfig = dataclasses.field(default_factory=LoggingConfig)
    source: str = ""

    @property
    def default_endpoint(self) -> EndpointConfig:
        return self.pc_endpoints[0]

    def endpoint(self, name: str | None) -> EndpointConfig:
        if name is None:
            return self.default_endpoint
        for ep in self.pc_endpoints:
            if ep.name == name:
                return ep
        raise ConfigError(f"no endpoint named {name!r}; known: {', '.join(e.name for e in self.pc_endpoints)}")


def _build(cls, data: Any, where: str):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a mapping")
    names = {f.name for f in dataclasses.fields(cls)}
    unknown = sorted(set(data) - names)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {', '.join(unknown)}")
    try:
        return cls(**data)
    except TypeError as exc:
        missing = [f.name for f in dataclasses.fields(cls)
                   if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
                   and f.name not in data]
        raise ConfigError(f"{where}: missing {', '.join(missing) or exc}") from None


# Sections from the 2025 layout that no longer do anything; accepted so an
# existing /etc/pilink.yaml keeps working after an update.
_RETIRED = ("pi_ftp", "usb_watcher", "alerts")


def load_config(path: str | pathlib.Path = DEFAULT_PATH) -> Config:
    p = pathlib.Path(path)
    if not p.exists():
        raise ConfigError(f"config file not found: {p} (copy config/pilink.example.yaml there)")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{p} is not valid YAML: {exc}") from None
    unknown = sorted(set(raw) - {"paths", "pc_endpoints", "ui", "flash_drive", "logging", *_RETIRED})
    if unknown:
        raise ConfigError(f"unknown section(s): {', '.join(unknown)}")
    eps = raw.get("pc_endpoints") or []
    if not eps:
        raise ConfigError("pc_endpoints: at least one PC endpoint is required")
    cfg = Config(
        paths=_build(PathConfig, raw.get("paths"), "paths"),
        pc_endpoints=[_build(EndpointConfig, e, f"pc_endpoints[{i}]") for i, e in enumerate(eps)],
        ui=_build(UIConfig, raw.get("ui"), "ui"),
        flash_drive=_build(FlashConfig, raw.get("flash_drive"), "flash_drive"),
        logging=_build(LoggingConfig, raw.get("logging"), "logging"),
        source=str(p),
    )
    if cfg.paths.flash_mount != "auto" and not cfg.paths.flash_transfer_root.startswith(cfg.paths.flash_mount):
        raise ConfigError("paths.flash_transfer_root must be inside paths.flash_mount")
    return cfg
