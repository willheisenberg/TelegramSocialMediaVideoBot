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


@dataclass(frozen=True)
class DownloadedImage:
    file_path: Path
    title: str
    source_url: str
    is_gif: bool


class VideoDownloader:
    def __init__(
        self,
        download_dir: str,
        max_download_size_bytes: int,
        cookies_file_path: str | None = None,
        extractor_username: str | None = None,
        extractor_password: str | None = None,
        instagram_username: str | None = None,
        instagram_password: str | None = None,
        youtube_username: str | None = None,
        youtube_password: str | None = None,
        twitter_username: str | None = None,
        twitter_password: str | None = None,
        tiktok_username: str | None = None,
        tiktok_password: str | None = None,
    ) -> None:
        self.download_dir = Path(download_dir)
        self.max_download_size_bytes = max_download_size_bytes
        self.cookies_file_path = cookies_file_path
        self.extractor_username = extractor_username
        self.extractor_password = extractor_password
        
        self.instagram_username = instagram_username
        self.instagram_password = instagram_password
        self.youtube_username = youtube_username
        self.youtube_password = youtube_password
        self.twitter_username = twitter_username
        self.twitter_password = twitter_password
        self.tiktok_username = tiktok_username
        self.tiktok_password = tiktok_password
        
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, url: str) -> DownloadedVideo | DownloadedImage:
        is_image, is_gif = await asyncio.to_thread(self._check_if_image, url)
        if is_image:
            return await asyncio.to_thread(self._download_image_sync, url, is_gif)
        return await asyncio.to_thread(self._download_sync, url)

    def _check_if_image(self, url: str) -> tuple[bool, bool]:
        import urllib.parse
        import urllib.request
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.lower()
            if path.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".heic", ".heif")):
                return True, False
            if path.endswith(".gif"):
                return True, True

            # HTTP HEAD request
            req = urllib.request.Request(
                url,
                method="HEAD",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type.startswith("image/"):
                        is_gif = "image/gif" in content_type
                        return True, is_gif
            except Exception:
                # Fallback to GET with short timeout/read if HEAD is method not allowed
                req.method = "GET"
                with urllib.request.urlopen(req, timeout=5) as response:
                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type.startswith("image/"):
                        is_gif = "image/gif" in content_type
                        return True, is_gif
        except Exception:
            pass
        return False, False

    def _download_image_sync(self, url: str, is_gif: bool) -> DownloadedImage:
        import urllib.parse
        import urllib.request
        import uuid
        with tempfile.TemporaryDirectory(dir=self.download_dir) as tmp_dir:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.lower()
            ext = ".jpg"  # default
            for possible_ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".heic", ".heif"]:
                if path.endswith(possible_ext):
                    ext = possible_ext
                    break

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "image/png" in content_type:
                        ext = ".png"
                    elif "image/jpeg" in content_type:
                        ext = ".jpg"
                    elif "image/gif" in content_type:
                        ext = ".gif"
                    elif "image/webp" in content_type:
                        ext = ".webp"

                    data = response.read()
            except Exception as exc:
                raise DownloaderError(f"Download der Bilddatei fehlgeschlagen: {exc}") from exc

            if len(data) > self.max_download_size_bytes:
                raise DownloaderError("Die Bilddatei ist zu gross fuer den Upload in Telegram")

            filename = "image"
            url_filename = os.path.basename(path)
            if url_filename:
                name_part, _ = os.path.splitext(url_filename)
                if name_part:
                    filename = name_part[:50]

            tmp_path = Path(tmp_dir) / f"{filename}{ext}"
            tmp_path.write_bytes(data)

            persistent_path = self.download_dir / tmp_path.name
            if persistent_path.exists():
                persistent_path = self.download_dir / f"{filename}_{uuid.uuid4().hex[:8]}{ext}"

            tmp_path.replace(persistent_path)

            title = filename
            if title == "image":
                title = "Bild"

            return DownloadedImage(
                file_path=persistent_path,
                title=title,
                source_url=url,
                is_gif=is_gif
            )

    def _download_sync(self, url: str) -> DownloadedVideo | DownloadedImage:
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

            if self.cookies_file_path and os.path.exists(self.cookies_file_path):
                ydl_opts["cookiefile"] = self.cookies_file_path

            import urllib.parse
            domain = urllib.parse.urlparse(url).netloc.lower()

            username = None
            password = None

            if "instagram.com" in domain:
                username = self.instagram_username
                password = self.instagram_password
                try:
                    return self._download_via_gallery_dl(url, username, password)
                except Exception:
                    # Fallback to standard yt-dlp flow if gallery-dl fails
                    pass
            elif "youtube.com" in domain or "youtu.be" in domain:
                username = self.youtube_username
                password = self.youtube_password
            elif "twitter.com" in domain or "x.com" in domain:
                username = self.twitter_username
                password = self.twitter_password
            elif "tiktok.com" in domain:
                username = self.tiktok_username
                password = self.tiktok_password

            # Fallback to generic extractor credentials if no specific platform matches
            if not username:
                username = self.extractor_username
            if not password:
                password = self.extractor_password

            if username:
                ydl_opts["username"] = username
            if password:
                ydl_opts["password"] = password

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                    # Check if there are NO video/audio formats
                    has_video_formats = len(info.get("formats", [])) > 0 or (
                        info.get("entries") and any(
                            isinstance(entry, dict) and len(entry.get("formats", [])) > 0
                            for entry in info["entries"]
                        )
                    )

                    if not has_video_formats:
                        image_urls = []

                        # Case A: Playlist / Carousel entries
                        entries = info.get("entries")
                        if entries:
                            for entry in entries:
                                if not entry:
                                    continue
                                entry_url = entry.get("url")
                                if entry_url and any(ext in entry_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                                    image_urls.append(entry_url)
                                elif entry.get("thumbnails"):
                                    sorted_thumbs = sorted(
                                        entry["thumbnails"],
                                        key=lambda x: (x.get("width") or 0) * (x.get("height") or 0),
                                        reverse=True
                                    )
                                    if sorted_thumbs:
                                        image_urls.append(sorted_thumbs[0]["url"])
                        else:
                            # Case B: Single post
                            direct_url = info.get("url")
                            if direct_url and any(ext in direct_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                                image_urls.append(direct_url)
                            elif info.get("thumbnails"):
                                sorted_thumbs = sorted(
                                    info["thumbnails"],
                                    key=lambda x: (x.get("width") or 0) * (x.get("height") or 0),
                                    reverse=True
                                )
                                if sorted_thumbs:
                                    image_urls.append(sorted_thumbs[0]["url"])

                        if image_urls:
                            import urllib.parse
                            parsed_url = urllib.parse.urlparse(url)
                            query_params = urllib.parse.parse_qs(parsed_url.query)
                            img_index_val = query_params.get("img_index")

                            if img_index_val:
                                target_index = 0
                                try:
                                    # Instagram's img_index is 1-indexed (e.g. index 8 means element 7)
                                    target_index = int(img_index_val[0]) - 1
                                except ValueError:
                                    pass

                                if target_index < 0 or target_index >= len(image_urls):
                                    target_index = 0

                                target_image_url = image_urls[target_index]
                                is_gif = ".gif" in target_image_url.lower()
                                return self._download_image_sync(target_image_url, is_gif)
                            else:
                                # Return all images as a list (up to 10 for Telegram rules)
                                downloaded_images = []
                                for img_url in image_urls[:10]:
                                    try:
                                        is_gif = ".gif" in img_url.lower()
                                        downloaded = self._download_image_sync(img_url, is_gif)
                                        downloaded_images.append(downloaded)
                                    except Exception:
                                        pass
                                if not downloaded_images:
                                    raise DownloaderError("Keine Bilder konnten heruntergeladen werden")
                                if len(downloaded_images) == 1:
                                    return downloaded_images[0]
                                return downloaded_images

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

    def _download_single_gallery_item(self, selected_item: dict[str, Any], url: str, tmp_dir: str) -> DownloadedVideo | DownloadedImage:
        import urllib.request
        import urllib.parse
        import uuid
        
        video_url = selected_item.get("video_url")
        display_url = selected_item.get("display_url")
        
        is_video = video_url is not None
        download_url = video_url if is_video else display_url
        if not download_url:
            raise DownloaderError("Keine downloadbare Medien-URL gefunden")
            
        parsed_media = urllib.parse.urlparse(download_url)
        path_media = parsed_media.path.lower()
        
        ext = ".mp4" if is_video else ".jpg"
        for possible_ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".mp4", ".mov", ".mkv"]:
            if path_media.endswith(possible_ext):
                ext = possible_ext
                break
                
        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                if "image/png" in content_type:
                    ext = ".png"
                elif "image/jpeg" in content_type:
                    ext = ".jpg"
                elif "image/gif" in content_type:
                    ext = ".gif"
                elif "image/webp" in content_type:
                    ext = ".webp"
                elif "video/mp4" in content_type:
                    ext = ".mp4"
                    
                file_data = response.read()
        except Exception as exc:
            raise DownloaderError(f"Download fehlgeschlagen: {exc}") from exc
            
        if len(file_data) > self.max_download_size_bytes:
            raise DownloaderError("Die Mediendatei überschreitet die erlaubte Telegram-Größe")
            
        filename = selected_item.get("filename") or "media"
        filename = filename[:50]
        
        tmp_path = Path(tmp_dir) / f"{filename}{ext}"
        tmp_path.write_bytes(file_data)
        
        persistent_path = self.download_dir / tmp_path.name
        if persistent_path.exists():
            persistent_path = self.download_dir / f"{filename}_{uuid.uuid4().hex[:8]}{ext}"
            
        tmp_path.replace(persistent_path)
        
        title = selected_item.get("description") or selected_item.get("title") or filename
        if len(title) > 80:
            title = title[:80] + "..."
            
        if is_video:
            return DownloadedVideo(
                file_path=persistent_path,
                title=title,
                source_url=url,
                uploader=selected_item.get("fullname") or selected_item.get("username"),
            )
        else:
            is_gif = ext == ".gif"
            return DownloadedImage(
                file_path=persistent_path,
                title=title,
                source_url=url,
                is_gif=is_gif
            )

    def _download_via_gallery_dl(self, url: str, username: str | None = None, password: str | None = None) -> DownloadedVideo | DownloadedImage | list[DownloadedVideo | DownloadedImage]:
        import subprocess
        import json
        import urllib.request
        import urllib.parse
        import tempfile
        import uuid
        
        gallery_dl_path = Path(__file__).parent.parent / ".venv" / "bin" / "gallery-dl"
        if not gallery_dl_path.exists():
            gallery_dl_path = Path("gallery-dl")
            
        cmd = [str(gallery_dl_path)]
        if self.cookies_file_path and os.path.exists(self.cookies_file_path):
            cmd.extend(["--cookies", self.cookies_file_path])
        if username:
            cmd.extend(["--username", username])
        if password:
            cmd.extend(["--password", password])
        cmd.extend(["-j", url])
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
        except Exception as exc:
            raise DownloaderError(f"gallery-dl Extraktion fehlgeschlagen: {exc}") from exc
            
        media_items = []
        for item in data:
            if isinstance(item, list) and len(item) >= 3:
                code, media_url_val, metadata_dict = item[:3]
                if code == 3 and isinstance(metadata_dict, dict):
                    media_items.append(metadata_dict)
                    
        if not media_items:
            raise DownloaderError("Keine Medieninhalte in diesem Beitrag gefunden")
            
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        img_index_val = query_params.get("img_index")
        target_num = None
        if img_index_val:
            try:
                target_num = int(img_index_val[0])
            except ValueError:
                pass
                
        if target_num is not None:
            selected_item = None
            for item in media_items:
                if item.get("num") == target_num:
                    selected_item = item
                    break
            if selected_item is None:
                selected_item = media_items[0]
                
            with tempfile.TemporaryDirectory(dir=self.download_dir) as tmp_dir:
                return self._download_single_gallery_item(selected_item, url, tmp_dir)
        else:
            # Download all items sequentially (up to 10 for Telegram media group rules)
            downloaded_items = []
            with tempfile.TemporaryDirectory(dir=self.download_dir) as tmp_dir:
                for item in media_items[:10]:
                    try:
                        downloaded = self._download_single_gallery_item(item, url, tmp_dir)
                        downloaded_items.append(downloaded)
                    except Exception:
                        pass
                        
            if not downloaded_items:
                raise DownloaderError("Keine Medieninhalte aus diesem Beitrag konnten heruntergeladen werden")
                
            if len(downloaded_items) == 1:
                return downloaded_items[0]
            return downloaded_items
