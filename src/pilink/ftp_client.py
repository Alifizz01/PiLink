from __future__ import annotations

import ftplib
import os
import pathlib
from dataclasses import dataclass
from typing import Callable, Optional

from .logging_utils import get_logger

logger = get_logger(__name__)


ProgressCb = Callable[[str, int, int], None]


@dataclass(slots=True)
class FTPConnectionInfo:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = False


class FTPClient:
    def __init__(self, info: FTPConnectionInfo, timeout: int = 30) -> None:
        self.info = info
        self.timeout = timeout
        self._ftp: Optional[ftplib.FTP] = None

    def __enter__(self) -> "FTPClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        ftp_cls = ftplib.FTP_TLS if self.info.use_tls else ftplib.FTP
        self._ftp = ftp_cls(timeout=self.timeout)
        logger.info("Connecting to FTP %s:%s", self.info.host, self.info.port)
        self._ftp.connect(self.info.host, self.info.port)
        self._ftp.login(self.info.username, self.info.password)
        if isinstance(self._ftp, ftplib.FTP_TLS):
            self._ftp.prot_p()
        self._ftp.set_pasv(True)

    def close(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.quit()
            except OSError:
                self._ftp.close()
            finally:
                self._ftp = None

    # Download remote directory to local path
    def download_tree(
        self,
        remote_dir: str,
        local_dir: str,
        progress: Optional[ProgressCb] = None,
    ) -> None:
        if self._ftp is None:
            raise RuntimeError("FTP connection not established")
        pathlib.Path(local_dir).mkdir(parents=True, exist_ok=True)
        self._ftp.cwd(remote_dir)
        self._walk_download(remote_dir, local_dir, progress)

    def upload_tree(
        self,
        local_dir: str,
        remote_dir: str,
        progress: Optional[ProgressCb] = None,
    ) -> None:
        if self._ftp is None:
            raise RuntimeError("FTP connection not established")
        self._ensure_remote_dirs(remote_dir)
        total_bytes = self._dir_size(local_dir)
        sent = 0
        for root, _, files in os.walk(local_dir):
            rel = os.path.relpath(root, local_dir)
            remote_path = remote_dir if rel == "." else f"{remote_dir}/{rel}"
            self._ensure_remote_dirs(remote_path)
            for file_name in files:
                local_path = os.path.join(root, file_name)
                remote_file = f"{remote_path}/{file_name}"
                with open(local_path, "rb") as fh:
                    self._ftp.storbinary(f"STOR {remote_file}", fh, blocksize=32768)
                sent += os.path.getsize(local_path)
                if progress:
                    progress(remote_file, sent, total_bytes)

    def _walk_download(
        self,
        remote_dir: str,
        local_dir: str,
        progress: Optional[ProgressCb],
    ) -> None:
        assert self._ftp is not None
        original_dir = self._ftp.pwd()
        try:
            for item in self._ftp.mlsd():
                name, facts = item
                if name in (".", ".."):
                    continue
                remote_path = f"{remote_dir.rstrip('/')}/{name}"
                local_path = os.path.join(local_dir, name)
                if facts.get("type") == "dir":
                    pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)
                    self._ftp.cwd(remote_path)
                    self._walk_download(remote_path, local_path, progress)
                    self._ftp.cwd("..")
                else:
                    with open(local_path, "wb") as fh:
                        self._ftp.retrbinary(f"RETR {remote_path}", fh.write)
                    if progress:
                        size = int(facts.get("size", 0))
                        progress(remote_path, size, size)
        finally:
            self._ftp.cwd(original_dir)

    def _ensure_remote_dirs(self, remote_path: str) -> None:
        assert self._ftp is not None
        parts = remote_path.strip("/").split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            try:
                self._ftp.mkd(current)
            except ftplib.error_perm as exc:
                if not str(exc).startswith("550"):  # already exists
                    raise

    def _dir_size(self, path: str) -> int:
        total = 0
        for root, _, files in os.walk(path):
            for file_name in files:
                total += os.path.getsize(os.path.join(root, file_name))
        return total

