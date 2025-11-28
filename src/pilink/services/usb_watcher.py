from __future__ import annotations

import argparse
import queue
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..config import Config, load_config
from ..logging_utils import configure_logging, get_logger
from ..storage import copytree, ensure_dirs, write_checksum_manifest

logger = get_logger(__name__)


class MirrorHandler(FileSystemEventHandler):
    def __init__(self, config: Config, work_queue: "queue.Queue[Path]"):
        super().__init__()
        self.config = config
        self.work_queue = work_queue

    def on_created(self, event):
        if event.is_directory:
            self._enqueue(Path(event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            self._enqueue(Path(event.dest_path))

    def _enqueue(self, path: Path) -> None:
        logger.info("Detected new staging folder: %s", path)
        self.work_queue.put(path)


class USBMirrorService:
    def __init__(self, config: Config):
        self.config = config
        self.staging = Path(config.paths.pc_inbox)
        self.flash_root = Path(config.paths.flash_transfer_root)
        ensure_dirs(str(self.staging), str(self.flash_root))
        self.queue: "queue.Queue[Path]" = queue.Queue()
        self.observer = Observer()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)

    def start(self) -> None:
        handler = MirrorHandler(self.config, self.queue)
        self.observer.schedule(handler, str(self.staging), recursive=False)
        self.observer.start()
        logger.info("USB mirror watching %s", self.staging)
        self.worker.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping USB mirror...")
            self.observer.stop()
        self.observer.join()

    def _worker_loop(self) -> None:
        debounce = self.config.usb_watcher.debounce_seconds
        while True:
            path = self.queue.get()
            time.sleep(debounce)
            if not path.exists():
                continue
            dest = self.flash_root / path.name
            copytree(str(path), str(dest))
            write_checksum_manifest(str(dest), str(dest / "checksums.txt"))
            logger.info("Mirrored %s -> %s", path, dest)
            self.queue.task_done()


def main() -> None:
    parser = argparse.ArgumentParser(description="PiLink USB mirror service")
    parser.add_argument("--config", default="/etc/pilink.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    configure_logging(config.logging.log_file, config.logging.level)
    service = USBMirrorService(config)
    service.start()


if __name__ == "__main__":
    main()

