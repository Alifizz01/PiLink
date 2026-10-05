"""PiLink console UI. Runs full screen on tty1 (systemd) or in any terminal."""
from __future__ import annotations

import argparse
import sys

from textual.app import App

from ..config import DEFAULT_PATH, ConfigError, Config, load_config
from ..logging_utils import configure_logging
from ..transfer_manager import TransferManager
from .screens import HomeScreen


class PiLinkApp(App):
    CSS_PATH = "pilink.tcss"
    TITLE = "PiLink"
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, config: Config):
        super().__init__()
        self.manager = TransferManager(config)

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pilink-ui", description="PiLink console UI")
    ap.add_argument("--config", default=DEFAULT_PATH)
    a = ap.parse_args(argv)
    try:
        cfg = load_config(a.config)
    except ConfigError as exc:
        # Shown on tty1 before systemd restarts us: say exactly what to fix.
        print(f"\nPiLink cannot start: {exc}\n\nEdit {a.config} and reboot, or run: pilink doctor\n", file=sys.stderr)
        return 2
    configure_logging(cfg.logging.log_file, cfg.logging.level, fallback_dir=cfg.paths.log_dir)
    PiLinkApp(cfg).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
