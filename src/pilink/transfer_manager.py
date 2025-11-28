from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
from typing import Callable, Optional

from .config import Config, EndpointConfig, load_config
from .ftp_client import FTPClient, FTPConnectionInfo
from .logging_utils import configure_logging, get_logger
from .storage import copy_path, copytree, ensure_dirs, write_checksum_manifest

logger = get_logger(__name__)

ProgressHook = Callable[[str, int, int], None]


class TransferManager:
    def __init__(self, config: Config):
        self.config = config
        ensure_dirs(
            self.config.paths.staging_root,
            self.config.paths.pc_inbox,
            self.config.paths.flash_outbox,
            self.config.paths.log_dir,
            self.config.paths.flash_transfer_root,
        )

    def run_pc_to_flash(
        self,
        endpoint_name: Optional[str] = None,
        progress: Optional[ProgressHook] = None,
    ) -> str:
        endpoint = self._get_endpoint(endpoint_name)
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        local_target = os.path.join(self.config.paths.pc_inbox, timestamp)
        ensure_dirs(local_target)

        info = FTPConnectionInfo(
            host=endpoint.host,
            port=endpoint.port,
            username=endpoint.username,
            password=endpoint.password,
        )
        with FTPClient(info) as ftp:
            ftp.download_tree(endpoint.download_root, local_target, progress)

        flash_dest = os.path.join(self.config.paths.flash_transfer_root, timestamp)
        copytree(local_target, flash_dest)
        write_checksum_manifest(flash_dest, os.path.join(flash_dest, "checksums.txt"))
        logger.info("Computer → Flash complete: %s", flash_dest)
        return flash_dest

    def run_flash_to_pc(
        self,
        selection: str,
        endpoint_name: Optional[str] = None,
        progress: Optional[ProgressHook] = None,
    ) -> str:
        endpoint = self._get_endpoint(endpoint_name)
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        staging = os.path.join(self.config.paths.flash_outbox, timestamp)
        path_obj = pathlib.Path(selection)
        dest = staging if path_obj.is_dir() else os.path.join(staging, path_obj.name)
        copy_path(selection, dest)

        info = FTPConnectionInfo(
            host=endpoint.host,
            port=endpoint.port,
            username=endpoint.username,
            password=endpoint.password,
        )
        with FTPClient(info) as ftp:
            ftp.upload_tree(staging, endpoint.upload_root, progress)

        logger.info("Flash → Computer complete: %s -> %s", staging, endpoint.upload_root)
        return endpoint.upload_root

    def _get_endpoint(self, name: Optional[str]) -> EndpointConfig:
        if name is None:
            return self.config.default_endpoint
        for endpoint in self.config.pc_endpoints:
            if endpoint.name == name:
                return endpoint
        raise ValueError(f"Endpoint {name} not found")


def cli() -> None:
    parser = argparse.ArgumentParser(description="PiLink transfer manager utility")
    parser.add_argument("--config", default="/etc/pilink.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    pc2flash = sub.add_parser("pc-to-flash")
    pc2flash.add_argument("--endpoint")

    flash2pc = sub.add_parser("flash-to-pc")
    flash2pc.add_argument("selection", help="Path on flash drive to upload")
    flash2pc.add_argument("--endpoint")

    args = parser.parse_args()
    config = load_config(args.config)
    configure_logging(config.logging.log_file, config.logging.level)
    manager = TransferManager(config)

    if args.command == "pc-to-flash":
        manager.run_pc_to_flash(endpoint_name=args.endpoint)
    else:
        manager.run_flash_to_pc(selection=args.selection, endpoint_name=args.endpoint)


if __name__ == "__main__":
    cli()

