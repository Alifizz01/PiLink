"""Regenerate the README screenshots from the real UI, driven through the demo.

    pip install -e ".[dev]" playwright && python tools/screenshots.py

Each screen is exported by Textual as SVG and rendered to PNG in Chrome, so
GitHub shows exactly what the console shows.
"""
import asyncio
import pathlib
import tempfile
import time

from playwright.sync_api import sync_playwright

import pilink.transfer_manager as tm
from pilink.config import load_config
from pilink.demo import prepare
from pilink.ui.app import PiLinkApp
from pilink.ui.screens import FlashTree, HomeScreen

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "img"
SIZE = (110, 34)


async def capture(cfg_path, svgs: dict):
    app = PiLinkApp(load_config(cfg_path))
    async with app.run_test(size=SIZE) as pilot:
        async def settle(cond, timeout=20):
            for _ in range(int(timeout / 0.1)):
                await pilot.pause(0.1)
                if cond():
                    return
        await settle(lambda: isinstance(app.screen, HomeScreen) and "waiting" in str(app.screen.query_one("#st-pc").render()))
        svgs["home"] = app.export_screenshot()

        # slow the copy down so the progress screen can be caught mid-flight
        real = tm.TransferManager._reporter

        def slow(self, progress, cancel):
            report = real(self, progress, cancel)
            def wrapped(phase, *a, **kw):
                if phase in ("download", "copy"):
                    time.sleep(0.03)
                return report(phase, *a, **kw)
            return wrapped
        tm.TransferManager._reporter = slow
        await pilot.press("1")
        await settle(lambda: getattr(app.screen, "phase", "") == "download")
        await pilot.pause(2.5)
        svgs["transfer"] = app.export_screenshot()
        await settle(lambda: app.screen.query_one("#result").display, 60)
        tm.TransferManager._reporter = real
        svgs["done"] = app.export_screenshot()

        await pilot.press("enter", "2")
        await pilot.pause(0.4)
        tree = app.screen.query_one(FlashTree)
        for name in ("Measurements", "Signed contract.pdf"):
            for i in range(tree.last_line + 1):
                tree.cursor_line = i
                if tree.cursor_node and tree.cursor_node.data and tree.cursor_node.data.path.name == name:
                    break
            await pilot.press("space")
        await pilot.pause(0.2)
        svgs["picker"] = app.export_screenshot()
        await pilot.press("u")
        await settle(lambda: getattr(app.screen, "running", True) is False)
        await pilot.press("enter", "4")
        await pilot.pause(0.3)
        svgs["history"] = app.export_screenshot()
        await pilot.press("escape", "5")
        await settle(lambda: "FTP login" in str(app.screen.query_one("#diag").render()))
        svgs["diagnostics"] = app.export_screenshot()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="pilink-shots-"))
    cfg_path, server, _ = prepare(str(work))
    svgs: dict = {}
    try:
        asyncio.run(capture(cfg_path, svgs))
    finally:
        server.close_all()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        page = b.new_page(device_scale_factor=1.5)
        for name, svg in svgs.items():
            f = work / f"{name}.svg"
            f.write_text(svg, encoding="utf-8")
            page.goto(f.as_uri())
            page.wait_for_timeout(500)
            box = page.locator("svg").bounding_box()
            page.set_viewport_size({"width": int(box["width"]) + 2, "height": int(box["height"]) + 2})
            page.locator("svg").screenshot(path=str(OUT / f"{name}.png"))
        b.close()
    print("screenshots:", ", ".join(sorted(svgs)))


if __name__ == "__main__":
    main()
