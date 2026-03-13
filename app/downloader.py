from __future__ import annotations

import asyncio
import contextlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


class DownloaderError(Exception):
    pass


@dataclass(frozen=True)
class DownloadedVideo:
    file_path: Path
    title: str
    source_url: str
    uploader: str | None


class VideoDownloader:
    def __init__(self, download_dir: str, max_download_size_bytes: int) -> None:
        self.download_dir = Path(download_dir)
        self.max_download_size_bytes = max_download_size_bytes
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, url: str) -> DownloadedVideo:
        return await asyncio.to_thread(self._download_sync, url)

    def _download_sync(self, url: str) -> DownloadedVideo:
        with tempfile.TemporaryDirectory(dir=self.download_dir) as tmp_dir:
            output_template = os.path.join(tmp_dir, "%(title).80s-%(id)s.%(ext)s")
            ydl_opts: dict[str, Any] = {
                "outtmpl": output_template,
                "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "restrictfilenames": True,
            }

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self._ensure_size_is_allowed(info)
                    downloaded_info = ydl.extract_info(url, download=True)
                    final_path = Path(ydl.prepare_filename(downloaded_info))
            except DownloadError as exc:
                raise DownloaderError(f"Download failed: {exc}") from exc

            if final_path.suffix != ".mp4":
                candidate = final_path.with_suffix(".mp4")
                if candidate.exists():
                    final_path = candidate

            if not final_path.exists():
                raise DownloaderError("Downloaded file could not be found")

            size = final_path.stat().st_size
            if size > self.max_download_size_bytes:
                raise DownloaderError("The downloaded video is too large for Telegram upload")

            persistent_path = self.download_dir / final_path.name
            final_path.replace(persistent_path)

            return DownloadedVideo(
                file_path=persistent_path,
                title=str(downloaded_info.get("title") or "video"),
                source_url=str(downloaded_info.get("webpage_url") or url),
                uploader=downloaded_info.get("uploader"),
            )

    def _ensure_size_is_allowed(self, info: dict[str, Any]) -> None:
        size_candidates = [
            info.get("filesize"),
            info.get("filesize_approx"),
        ]

        requested_formats = info.get("requested_formats") or []
        for fmt in requested_formats:
            size_candidates.append(fmt.get("filesize"))
            size_candidates.append(fmt.get("filesize_approx"))

        formats = info.get("formats") or []
        for fmt in formats:
            size_candidates.append(fmt.get("filesize"))
            size_candidates.append(fmt.get("filesize_approx"))

        known_sizes = [size for size in size_candidates if isinstance(size, int)]
        if known_sizes and min(known_sizes) > self.max_download_size_bytes:
            raise DownloaderError("The source video exceeds the configured upload size limit")

    def cleanup(self, file_path: Path) -> None:
        with contextlib.suppress(FileNotFoundError):
            file_path.unlink()
