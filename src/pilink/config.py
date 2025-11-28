from __future__ import annotations

import dataclasses
import pathlib
import typing as t

import yaml


@dataclasses.dataclass(slots=True)
class UIConfig:
    theme: str = "blue"
    log_lines: int = 200


@dataclasses.dataclass(slots=True)
class PathConfig:
    staging_root: str
    pc_inbox: str
    flash_outbox: str
    log_dir: str
    flash_mount: str
    flash_transfer_root: str
    retention_days: int = 7


@dataclasses.dataclass(slots=True)
class EndpointConfig:
    name: str
    host: str
    port: int
    username: str
    password: str
    download_root: str
    upload_root: str


@dataclasses.dataclass(slots=True)
class PiFTPConfig:
    host: str
    port: int
    username: str
    password: str
    root: str


@dataclasses.dataclass(slots=True)
class USBWatcherConfig:
    enabled: bool = True
    debounce_seconds: int = 5


@dataclasses.dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "/var/log/pilink.log"


@dataclasses.dataclass(slots=True)
class AlertsConfig:
    enable_sound: bool = False
    enable_gpio_led: bool = False


@dataclasses.dataclass(slots=True)
class Config:
    ui: UIConfig
    paths: PathConfig
    pc_endpoints: list[EndpointConfig]
    pi_ftp: PiFTPConfig
    usb_watcher: USBWatcherConfig
    logging: LoggingConfig
    alerts: AlertsConfig

    @property
    def default_endpoint(self) -> EndpointConfig:
        return self.pc_endpoints[0]


def _load_dataclass(cls: t.Type[t.Any], data: t.Mapping[str, t.Any]) -> t.Any:
    return cls(**data)


def _load_list(cls: t.Type[t.Any], items: t.Iterable[t.Mapping[str, t.Any]]) -> list[t.Any]:
    return [cls(**item) for item in items]


def load_config(path: str | pathlib.Path) -> Config:
    cfg_path = pathlib.Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    return Config(
        ui=_load_dataclass(UIConfig, raw.get("ui", {})),
        paths=_load_dataclass(PathConfig, raw["paths"]),
        pc_endpoints=_load_list(EndpointConfig, raw["pc_endpoints"]),
        pi_ftp=_load_dataclass(PiFTPConfig, raw["pi_ftp"]),
        usb_watcher=_load_dataclass(USBWatcherConfig, raw.get("usb_watcher", {})),
        logging=_load_dataclass(LoggingConfig, raw.get("logging", {})),
        alerts=_load_dataclass(AlertsConfig, raw.get("alerts", {})),
    )

