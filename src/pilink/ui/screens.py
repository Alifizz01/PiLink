from __future__ import annotations

from typing import Callable

from textual import events
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Log, Static


class HomeScreen(Screen):
    BINDINGS = [("q", "app.quit", "Quit"), ("l", "view_log", "Log")]

    class TransferRequest(Message):
        def __init__(self, sender: Screen, mode: str):
            super().__init__()
            self.sender = sender
            self.mode = mode

    status_text = reactive("Idle")

    def compose(self):
        yield Footer()
        yield Vertical(
            Static("PiLink Transfer Hub", classes="title"),
            Static("Select a transfer mode:", classes="subtitle"),
            Horizontal(
                Button("Computer → Flash", id="pc2flash", variant="primary"),
                Button("Flash → Computer", id="flash2pc", variant="primary"),
                classes="actions",
            ),
            Static("Status: Idle", classes="status", id="status-label"),
            Log(classes="log", id="pilink-log"),
            id="home",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pc2flash":
            self.post_message(self.TransferRequest(self, "pc2flash"))
        elif event.button.id == "flash2pc":
            self.post_message(self.TransferRequest(self, "flash2pc"))

    def action_view_log(self) -> None:
        log_widget = self.query_one("#pilink-log", expect_type=Log)
        log_widget.visible = not log_widget.visible

    def watch_status_text(self, value: str) -> None:
        label = self.query_one("#status-label", expect_type=Static)
        label.update(f"Status: {value}")

