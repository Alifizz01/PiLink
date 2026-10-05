"""PiLink screens: home dashboard, flash file picker, transfer, history, diagnostics."""
from __future__ import annotations

import datetime as dt
import os
import threading
import time
from pathlib import Path
from typing import Iterable

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, DirectoryTree, ProgressBar, Static

from .. import __version__, history
from ..errors import PiLinkError
from ..storage import free_bytes, human
from ..transfer_manager import PHASES, Progress


def bars(title: str, keys: str) -> ComposeResult:
    yield Static(f" PiLink Transfer Hub  ·  {title}", id="titlebar")
    yield Static(keys.replace("[#FFD34D b]", "[b #FFFFFF on #0A2A8A] ").replace("[/] ", " [/] "), id="keybar")


def k(key: str, label: str) -> str:
    return f"[#FFD34D b]{key}[/] {label}   "


# =================================================================== home
class HomeScreen(Screen):
    BINDINGS = [
        Binding("1", "pc_to_flash", "Computer → Flash"),
        Binding("2", "flash_to_pc", "Flash → Computer"),
        Binding("3", "eject", "Remove flash"),
        Binding("4", "history", "History"),
        Binding("5", "diagnostics", "Diagnostics"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield from bars("Home", k("1-5", "choose") + k("R", "refresh status") + k("Q", "quit"))
        with Vertical(classes="frame", id="status") as v:
            v.border_title = "Status"
            yield Static(id="st-pc", classes="row")
            yield Static(id="st-flash", classes="row")
            yield Static(id="st-pi", classes="row")
        with Vertical(classes="frame", id="menu") as v:
            v.border_title = "Transfer"
            yield Static(id="a1", classes="action")
            yield Static(id="a2", classes="action")
            yield Static(id="a3", classes="action")
            yield Static(f"  {k('4', 'History')}  {k('5', 'Diagnostics')}", classes="row")
        with Vertical(classes="frame", id="last") as v:
            v.border_title = "Last transfer"
            yield Static(id="last-text", classes="row")

    def on_mount(self) -> None:
        self.pc_line = "[#9AA6C8]checking the PC…[/]"
        self.pc_ok = False
        self.set_interval(2.0, self.refresh_local)
        self.set_interval(15.0, self.check_pc)
        self.refresh_local()
        self.check_pc()

    def on_screen_resume(self) -> None:
        self.refresh_local()
        self.check_pc()

    # ---- status
    def check_pc(self) -> None:
        mgr = self.app.manager
        ep = mgr.config.default_endpoint

        def work():
            try:
                line = f"[#6EF08A]●[/] [b]{ep.name}[/] {ep.host}  ·  {mgr.check_pc()}"
                ok = True
            except PiLinkError as exc:
                line, ok = f"[#FF7A7A]●[/] [b]{ep.name}[/] {ep.host}  ·  [#FF7A7A]{exc}[/]", False
            self.app.call_from_thread(self._set_pc, line, ok)
        threading.Thread(target=work, daemon=True).start()

    def _set_pc(self, line: str, ok: bool) -> None:
        self.pc_line, self.pc_ok = line, ok
        self.refresh_local()

    def refresh_local(self) -> None:
        mgr = self.app.manager
        fl = mgr.flash_status()
        self.query_one("#st-pc", Static).update(f"[b]PC   [/] {self.pc_line}")
        if fl.present:
            used = 1 - fl.free / fl.total if fl.total else 0
            gauge = "█" * round(used * 20) + "░" * (20 - round(used * 20))
            self.query_one("#st-flash", Static).update(
                f"[b]Flash[/] [#6EF08A]●[/] [b]{fl.label}[/]  {gauge}  {human(fl.free)} free of {human(fl.total)}"
                + ("" if fl.writable else f"  [#FF7A7A]{fl.note}[/]"))
        else:
            self.query_one("#st-flash", Static).update(f"[b]Flash[/] [#FFD34D]○[/] {fl.note}")
        self.query_one("#st-pi", Static).update(
            f"[b]Pi   [/] staging {human(free_bytes(mgr.config.paths.staging_root))} free  ·  "
            f"{dt.datetime.now():%H:%M:%S}")
        ready = fl.present and fl.writable
        self._action("#a1", "1", "Computer  →  Flash drive", "copy everything waiting on the PC onto the stick",
                     ready and self.pc_ok)
        self._action("#a2", "2", "Flash drive  →  Computer", "choose files on the stick and send them to the PC",
                     ready and self.pc_ok)
        self._action("#a3", "3", "Safely remove flash drive", "flush and unmount, then pull the stick", fl.present)
        recs = history.load(mgr.config.paths.staging_root, 1)
        if recs:
            r = recs[0]
            mark = "[#6EF08A]✓[/]" if r.ok else "[#FF7A7A]✗[/]"
            what = "Computer → Flash" if r.direction == "pc-to-flash" else "Flash → Computer"
            detail = (f"{r.files} files, {human(r.bytes)}, {'verified' if r.verified else 'sizes not checked'}"
                      if r.ok else f"[#FF7A7A]{r.error}[/]")
            self.query_one("#last-text", Static).update(f"{mark} {r.when.replace('T', ' ')}  {what}  ·  {detail}")
        else:
            self.query_one("#last-text", Static).update("[#9AA6C8]No transfers yet.[/]")

    def _action(self, sel, key, title, sub, enabled):
        w = self.query_one(sel, Static)
        w.set_class(not enabled, "disabled")
        style = "#FFD34D b" if enabled else "#6C7BAA"
        w.update(f"[{style}][{key}][/]  [b]{title}[/]\n     [#9AA6C8]{sub}[/]")

    # ---- actions
    def action_refresh(self) -> None:
        self.refresh_local()
        self.check_pc()

    def action_pc_to_flash(self) -> None:
        self.app.push_screen(TransferScreen("pc-to-flash"))

    def action_flash_to_pc(self) -> None:
        fl = self.app.manager.flash_status()
        if not fl.present:
            self.app.notify(fl.note, severity="warning")
            return
        self.app.push_screen(PickScreen())

    def action_eject(self) -> None:
        try:
            self.app.notify(self.app.manager.eject(), title="Flash drive", timeout=8)
        except PiLinkError as exc:
            self.app.notify(str(exc), severity="error", timeout=12)
        self.refresh_local()

    def action_history(self) -> None:
        self.app.push_screen(HistoryScreen())

    def action_diagnostics(self) -> None:
        self.app.push_screen(DiagnosticsScreen())


# =================================================================== picker
class FlashTree(DirectoryTree):
    """The stick's files, without system folders, with a tick on what is selected."""

    # Tree binds Space to expand/collapse; on the picker Space means "select".
    # Enter and the right arrow still open folders.
    BINDINGS = [Binding("space", "screen.toggle", "Select", show=False),
                Binding("right", "expand", "Open", show=False)]

    def action_expand(self) -> None:
        node = self.cursor_node
        if node is not None and node.allow_expand and not node.is_expanded:
            node.expand()

    def __init__(self, path: str, hidden: Iterable[str], **kw):
        super().__init__(path, **kw)
        self.hidden = set(hidden)
        self.selected: set[Path] = set()

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [p for p in paths if p.name not in self.hidden and not p.name.startswith(".")]

    def render_label(self, node, base_style, style) -> Text:
        label = super().render_label(node, base_style, style)
        path = node.data.path if node.data else None
        mark = Text("✔ ", style="bold #6EF08A") if path in self.selected else Text("  ")
        return mark + label


class PickScreen(Screen):
    BINDINGS = [
        Binding("space", "toggle", "Select"),
        Binding("u", "upload", "Upload"),
        Binding("a", "all", "Whole stick"),
        Binding("c", "clear", "Clear"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        mgr = self.app.manager
        yield from bars("Flash drive → Computer",
                        k("↑↓", "move") + k("→/Enter", "open folder") + k("Space", "select") +
                        k("A", "whole stick") + k("U", "upload") + k("Esc", "back"))
        with Horizontal(id="pick-body"):
            tree = FlashTree(mgr.mount(), mgr.config.flash_drive.hidden, id="tree")
            tree.border_title = "Flash drive"
            yield tree
            with Vertical(id="selection") as v:
                v.border_title = "Selected"
                yield Static(id="sel-text")

    def on_mount(self) -> None:
        self.query_one(FlashTree).focus()
        self.update_selection()

    def update_selection(self) -> None:
        tree = self.query_one(FlashTree)
        if not tree.selected:
            self.query_one("#sel-text", Static).update(
                "[#9AA6C8]Nothing yet.\n\nMove to a file or folder\nand press [#FFD34D b]Space[/].\n\n"
                "[#FFD34D b]A[/] selects the whole stick.[/]")
            return
        mount = self.app.manager.mount()
        size = 0
        for p in tree.selected:
            size += sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
        names = sorted(os.path.relpath(p, mount) for p in tree.selected)
        shown = "\n".join(f"[#6EF08A]✔[/] {'(whole stick)' if n == '.' else n}" for n in names[:14])
        more = f"\n[#9AA6C8]…and {len(names) - 14} more[/]" if len(names) > 14 else ""
        self.query_one("#sel-text", Static).update(
            f"{shown}{more}\n\n[b]{len(names)} item(s), {human(size)}[/]\n\n[#FFD34D b]U[/] upload to the PC")

    def action_toggle(self) -> None:
        tree = self.query_one(FlashTree)
        node = tree.cursor_node
        if node is None or node.data is None:
            return
        tree.selected.symmetric_difference_update({node.data.path})
        node.refresh()
        self.update_selection()

    def action_all(self) -> None:
        tree = self.query_one(FlashTree)
        tree.selected = {Path(self.app.manager.mount())}
        tree.refresh()
        self.update_selection()

    def action_clear(self) -> None:
        tree = self.query_one(FlashTree)
        tree.selected.clear()
        tree.refresh()
        self.update_selection()

    def action_upload(self) -> None:
        tree = self.query_one(FlashTree)
        if not tree.selected:
            self.app.notify("Select something first (Space).", severity="warning")
            return
        self.app.switch_screen(TransferScreen("flash-to-pc", sorted(str(p) for p in tree.selected)))


# =================================================================== transfer
STEPS = {
    "pc-to-flash": ["connect", "list", "download", "hash", "copy", "verify"],
    "flash-to-pc": ["stage", "hash", "connect", "upload", "verify"],
}


class TransferScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel_or_back", "Cancel / back"),
        Binding("enter", "back", "Home", show=False),
        Binding("3", "eject", "Remove flash", show=False),
    ]

    def __init__(self, direction: str, selection: list[str] | None = None):
        super().__init__()
        self.direction, self.selection = direction, selection or []
        self.cancel = threading.Event()
        self.running = True
        self.phase = ""
        self.seen: list[str] = []
        self.t0 = time.monotonic()
        self.rate_mark = (time.monotonic(), 0)
        self.rate = 0.0

    def compose(self) -> ComposeResult:
        title = "Computer → Flash drive" if self.direction == "pc-to-flash" else "Flash drive → Computer"
        yield from bars(title, k("Esc", "cancel"))
        with Vertical(classes="frame", id="steps") as v:
            v.border_title = title
            yield Static(id="step-list")
            yield Static(id="gap")
            yield ProgressBar(total=100, show_eta=False, id="bar")
            yield Static(id="now", classes="row")
            yield Static(id="speed", classes="row")
        yield Static(id="result")

    def on_mount(self) -> None:
        self.query_one("#result").display = False
        self.draw_steps()
        threading.Thread(target=self.work, daemon=True).start()

    # ---- worker thread
    def work(self) -> None:
        mgr = self.app.manager

        def progress(p: Progress):
            self.app.call_from_thread(self.on_progress, p)
        try:
            if self.direction == "pc-to-flash":
                res = mgr.run_pc_to_flash(progress=progress, cancel=self.cancel)
            else:
                res = mgr.run_flash_to_pc(self.selection, progress=progress, cancel=self.cancel)
            self.app.call_from_thread(self.finish, res, None)
        except PiLinkError as exc:
            self.app.call_from_thread(self.finish, None, str(exc))

    # ---- UI thread
    def on_progress(self, p: Progress) -> None:
        if p.phase != self.phase:
            if p.phase not in self.seen:
                self.seen.append(p.phase)
            self.phase = p.phase
            self.rate_mark, self.rate = (time.monotonic(), p.done), 0.0
            self.draw_steps(p.message)
        bar = self.query_one(ProgressBar)
        if p.total:
            bar.update(total=p.total, progress=p.done)
        if p.phase in ("download", "copy", "upload", "stage") and p.total:
            t, d = self.rate_mark
            now = time.monotonic()
            if now - t > 0.5:
                self.rate = (p.done - d) / (now - t)
                self.rate_mark = (now, p.done)
            eta = (p.total - p.done) / self.rate if self.rate > 0 else 0
            self.query_one("#speed", Static).update(
                f"[#9AA6C8]{human(p.done)} of {human(p.total)}"
                + (f"  ·  {human(self.rate)}/s  ·  about {int(eta)} s left" if self.rate else "") + "[/]")
        elif p.phase in ("verify", "hash") and p.total:
            self.query_one("#speed", Static).update(f"[#9AA6C8]{p.done} of {p.total} files[/]")
        if p.file:
            self.query_one("#now", Static).update(f"[#9AA6C8]file:[/] {p.file}")

    def draw_steps(self, message: str = "") -> None:
        lines = []
        for step in STEPS[self.direction]:
            if step == self.phase and self.running:
                lines.append(f"[#FFD34D b]▶ {PHASES[step]}[/]  [#9AA6C8]{message if message != PHASES[step] else ''}[/]")
            elif step in self.seen:
                lines.append(f"[#6EF08A]✓[/] {PHASES[step]}")
            else:
                lines.append(f"[#6C7BAA]· {PHASES[step]}[/]")
        self.query_one("#step-list", Static).update("\n".join(lines))

    def finish(self, res, error) -> None:
        self.running = False
        result = self.query_one("#result", Static)
        result.display = True
        secs = time.monotonic() - self.t0
        if res is not None:
            self.seen = list(STEPS[self.direction])
            self.phase = "done"
            self.draw_steps()
            bar = self.query_one(ProgressBar)
            bar.update(total=max(res.bytes, 1), progress=max(res.bytes, 1))
            check = "verified byte for byte" if res.verified else "sent (the PC did not report sizes to check)"
            tail = ("Press [b]3[/] to remove the flash drive safely, or [b]Enter[/] for the home screen."
                    if self.direction == "pc-to-flash" else "Press [b]Enter[/] for the home screen.")
            result.update(f"✓  Done: {res.files} file(s), {human(res.bytes)} in {secs:.1f} s, {check}.\n"
                          f"   {res.destination}\n\n   {tail}")
            result.set_classes("success")
        else:
            self.draw_steps()
            result.update(f"✗  {error}\n\n   Press [b]Enter[/] for the home screen.")
            result.set_classes("failure")
        keys = k("Enter", "home") + (k("3", "remove flash") if res else "")
        self.query_one("#keybar", Static).update(keys.replace("[#FFD34D b]", "[b #FFFFFF on #0A2A8A] ").replace("[/] ", " [/] "))

    def action_cancel_or_back(self) -> None:
        if self.running:
            self.cancel.set()
            self.app.notify("Cancelling after the current block…", severity="warning")
        else:
            self.app.pop_screen()

    def action_back(self) -> None:
        if not self.running:
            self.app.pop_screen()

    def action_eject(self) -> None:
        if self.running:
            return
        try:
            self.app.notify(self.app.manager.eject(), title="Flash drive", timeout=8)
        except PiLinkError as exc:
            self.app.notify(str(exc), severity="error", timeout=12)


# =================================================================== history
class HistoryScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield from bars("History", k("↑↓", "scroll") + k("Esc", "back"))
        yield DataTable(id="hist", zebra_stripes=False, cursor_type="row")

    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns("", "When", "Direction", "Files", "Size", "Time", "Result")
        for r in history.load(self.app.manager.config.paths.staging_root):
            t.add_row("[#6EF08A]✓[/]" if r.ok else "[#FF7A7A]✗[/]", r.when.replace("T", " "),
                      "PC → Flash" if r.direction == "pc-to-flash" else "Flash → PC",
                      str(r.files) if r.ok else "", human(r.bytes) if r.ok else "", f"{r.seconds:.1f} s",
                      ("verified" if r.verified else "sent") if r.ok else r.error[:70])
        if not t.row_count:
            t.add_row("", "No transfers yet.", "", "", "", "", "")
        t.focus()


# =================================================================== diagnostics
class DiagnosticsScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Back"), Binding("r", "run", "Run again")]

    def compose(self) -> ComposeResult:
        yield from bars("Diagnostics", k("R", "run again") + k("Esc", "back"))
        with Vertical(classes="frame") as v:
            v.border_title = "Checks"
            yield Static(id="diag")

    def on_mount(self) -> None:
        self.action_run()

    def action_run(self) -> None:
        self.query_one("#diag", Static).update("[#9AA6C8]running…[/]")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        from ..doctor import run_checks
        lines = []
        for ok, name, detail in run_checks(self.app.manager.config):
            mark = {True: "[#6EF08A]✓[/]", False: "[#FF7A7A]✗[/]", None: "[#FFD34D]![/]"}[ok]
            lines.append(f"{mark} [b]{name}[/]\n   [#9AA6C8]{detail}[/]")
        lines.append(f"\n[#9AA6C8]PiLink {__version__}  ·  config {self.app.manager.config.source}[/]")
        self.app.call_from_thread(self.query_one("#diag", Static).update, "\n".join(lines))
