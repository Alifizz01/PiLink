"""Drive the real UI headless, with the keys a person would press."""
import asyncio
import os

from textual.widgets import Static

from pilink.config import load_config
from pilink.demo import prepare
from pilink.ui.app import PiLinkApp
from pilink.ui.screens import FlashTree, HomeScreen, PickScreen, TransferScreen


async def wait_for(pilot, cond, timeout=20.0):
    for _ in range(int(timeout / 0.1)):
        await pilot.pause(0.1)
        if cond():
            return True
    return False


def text(app, sel):
    return str(app.screen.query_one(sel, Static).render())


def test_both_workflows_through_the_ui(tmp_path):
    cfg_path, server, root = prepare(str(tmp_path / "demo"))
    try:
        async def scenario():
            app = PiLinkApp(load_config(cfg_path))
            async with app.run_test(size=(100, 34)) as pilot:
                assert await wait_for(pilot, lambda: isinstance(app.screen, HomeScreen)
                                      and "waiting" in text(app, "#st-pc"))
                assert "free of" in text(app, "#st-flash")

                # 1: Computer -> Flash
                await pilot.press("1")
                assert isinstance(app.screen, TransferScreen)
                assert await wait_for(pilot, lambda: app.screen.query_one("#result").display)
                assert "Done: 7 file(s)" in text(app, "#result") and "verified" in text(app, "#result")
                await pilot.press("enter")
                assert isinstance(app.screen, HomeScreen)
                assert any((root / "flash-drive" / "transfers").iterdir())

                # 2: Flash -> Computer, picking one folder with the keyboard
                await pilot.press("2")
                assert isinstance(app.screen, PickScreen)
                tree = app.screen.query_one(FlashTree)
                await pilot.pause(0.3)
                for i in range(tree.last_line + 1):           # move the cursor onto "Measurements"
                    tree.cursor_line = i
                    if tree.cursor_node and tree.cursor_node.data and tree.cursor_node.data.path.name == "Measurements":
                        break
                await pilot.press("space")
                assert "Measurements" in text(app, "#sel-text")
                await pilot.press("u")
                assert await wait_for(pilot, lambda: isinstance(app.screen, TransferScreen)
                                      and app.screen.query_one("#result").display)
                assert "Done: 3 file(s)" in text(app, "#result")
                sent = next((root / "pc" / "uploads").iterdir())
                assert sorted(os.listdir(sent / "Measurements")) == ["run-001.csv", "run-002.csv", "run-003.csv"]

                # history and diagnostics open and show what happened
                await pilot.press("enter", "4")
                await pilot.pause(0.2)
                assert app.screen.query_one("DataTable").row_count == 2
                await pilot.press("escape", "5")
                assert await wait_for(pilot, lambda: "FTP login" in text(app, "#diag"))
        asyncio.run(scenario())
    finally:
        server.close_all()
