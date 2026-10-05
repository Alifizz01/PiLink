"""pilink: everything the UI does, from a shell (over SSH, from scripts, from cron).

    pilink status                       what is connected, right now
    pilink doctor                       every check, with what to do when one fails
    pilink pc-to-flash                  copy the PC folder onto the stick, verified
    pilink flash-to-pc PATH [PATH ...]  send files/folders from the stick to the PC
    pilink eject                        flush and unmount the stick
    pilink history                      past transfers
    pilink ui                           the console UI (what tty1 runs)
    pilink demo                         try the whole thing on any computer, no Pi needed
"""
from __future__ import annotations

import argparse
import time
import sys

from . import __version__, history
from .config import DEFAULT_PATH, ConfigError, load_config
from .errors import PiLinkError
from .logging_utils import configure_logging
from .storage import human


_last_draw = [0.0]


def _bar(p) -> None:
    if p.total and p.phase in ("download", "copy", "upload", "stage"):
        # at most 5 redraws a second; when output is a log file, only the final line
        now = time.monotonic()
        finished = p.done >= p.total
        if not finished and (not sys.stderr.isatty() or now - _last_draw[0] < 0.2):
            return
        _last_draw[0] = now
        width = 30
        fill = int(width * p.done / p.total)
        sys.stderr.write(f"\r  {p.message:<28} [{'#' * fill}{'.' * (width - fill)}] "
                         f"{human(p.done):>9} / {human(p.total):<9}")
        if p.done >= p.total:
            sys.stderr.write("\n")
    elif p.phase not in ("download", "copy", "upload", "stage"):
        if p.phase in ("verify", "hash") and p.done not in (0, p.total):
            return
        sys.stderr.write(f"  {p.message}\n")
    sys.stderr.flush()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pilink", description="PiLink transfer hub")
    ap.add_argument("--config", default=DEFAULT_PATH)
    ap.add_argument("--version", action="version", version=f"pilink {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="what is connected right now")
    sub.add_parser("doctor", help="run every check")
    p2f = sub.add_parser("pc-to-flash", help="copy the PC folder onto the flash drive")
    p2f.add_argument("--endpoint")
    f2p = sub.add_parser("flash-to-pc", help="send files/folders from the flash drive to the PC")
    f2p.add_argument("paths", nargs="+", help="paths on the stick (relative to the mount, or absolute)")
    f2p.add_argument("--endpoint")
    sub.add_parser("eject", help="flush and unmount the flash drive")
    h = sub.add_parser("history", help="past transfers")
    h.add_argument("-n", type=int, default=20)
    sub.add_parser("ui", help="the console UI")
    d = sub.add_parser("demo", help="run the UI against a local fake PC and stick (needs pyftpdlib)")
    d.add_argument("--dir", help="where to put the demo files (default: a temp folder)")
    a = ap.parse_args(argv)

    if a.cmd == "demo":
        from .demo import run_demo
        return run_demo(a.dir)

    try:
        cfg = load_config(a.config)
    except ConfigError as exc:
        print(f"pilink: {exc}", file=sys.stderr)
        return 2
    configure_logging(cfg.logging.log_file, cfg.logging.level, fallback_dir=cfg.paths.log_dir)

    if a.cmd == "ui":
        from .ui.app import PiLinkApp
        PiLinkApp(cfg).run()
        return 0
    if a.cmd == "doctor":
        from .doctor import run_checks
        results = run_checks(cfg)
        for ok, name, detail in results:
            print(f"{ {True: '[ ok ]', False: '[FAIL]', None: '[warn]'}[ok]} {name}: {detail}")
        return 1 if any(ok is False for ok, *_ in results) else 0
    if a.cmd == "history":
        for r in history.load(cfg.paths.staging_root, a.n):
            what = "PC -> flash" if r.direction == "pc-to-flash" else "flash -> PC"
            tail = (f"{r.files} files, {human(r.bytes)}, {'verified' if r.verified else 'sent'}"
                    if r.ok else f"FAILED: {r.error}")
            print(f"{r.when}  {what:<12} {tail}")
        return 0

    from .transfer_manager import TransferManager
    mgr = TransferManager(cfg)
    try:
        if a.cmd == "status":
            fl = mgr.flash_status()
            print(f"flash: {f'{fl.label}, {human(fl.free)} free of {human(fl.total)}' if fl.present else fl.note}")
            try:
                print(f"pc:    {cfg.default_endpoint.host}: {mgr.check_pc()}")
            except PiLinkError as exc:
                print(f"pc:    {exc}")
            return 0
        if a.cmd == "eject":
            print(mgr.eject())
            return 0
        if a.cmd == "pc-to-flash":
            res = mgr.run_pc_to_flash(a.endpoint, progress=_bar)
        else:
            res = mgr.run_flash_to_pc(a.paths, a.endpoint, progress=_bar)
        print(f"done: {res.files} files, {human(res.bytes)} in {res.seconds:.1f} s -> {res.destination} "
              f"({'verified' if res.verified else 'sizes not reported by the server'})")
        return 0
    except PiLinkError as exc:
        print(f"\npilink: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
