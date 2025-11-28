from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from pathlib import Path

from textual.app import App, ComposeResult
from ..config import Config, load_config
from ..logging_utils import configure_logging, get_logger
from ..transfer_manager import TransferManager
from .screens import HomeScreen

logger = get_logger(__name__)


class PiLinkApp(App):
    CSS = """
    Screen {
        background: #001845;
        color: #d7e3ff;
    }
    #home {
        align: center middle;
        padding: 2;
        border: solid #2350a3;
        background: #022b6b;
    }
    .title {
        content-align: center middle;
        text-style: bold;
        padding: 1;
    }
    .actions Button {
        margin: 1 2;
        width: 24;
    }
    .log {
        height: 12;
        border: solid #133372;
        background: #000e2a;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.manager = TransferManager(config)
        self.home_screen: HomeScreen | None = None

    def compose(self) -> ComposeResult:
        self.home_screen = HomeScreen()
        yield self.home_screen

    async def on_home_screen_transfer_request(self, message: HomeScreen.TransferRequest):
        mode = message.mode
        if mode == "pc2flash":
            await self._run_transfer("Computer → Flash", self.manager.run_pc_to_flash)
        else:
            flash_path = str(Path(self.config.paths.flash_mount))
            await self._run_transfer(
                "Flash → Computer",
                lambda: self.manager.run_flash_to_pc(flash_path),
            )

    async def _run_transfer(self, label: str, func) -> None:
        if self.home_screen:
            self.home_screen.status_text = f"{label} running..."
            log_widget = self.home_screen.query_one("#pilink-log")
            log_widget.write(f"[{dt.datetime.now():%H:%M:%S}] {label} started")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, func)
        if self.home_screen:
            self.home_screen.status_text = f"{label} finished"
            log_widget = self.home_screen.query_one("#pilink-log")
            log_widget.write(f"[{dt.datetime.now():%H:%M:%S}] {label} complete: {result}")
        self.notify(f"{label} complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="PiLink UI")
    parser.add_argument("--config", default="/etc/pilink.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    configure_logging(config.logging.log_file, config.logging.level)
    app = PiLinkApp(config)
    app.run()


if __name__ == "__main__":
    main()

