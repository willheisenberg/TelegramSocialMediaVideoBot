import shutil
import subprocess
from pathlib import Path

import pytest

from app.downloader import VideoDownloader, split_music_item

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="ffmpeg/ffprobe nicht installiert",
)


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _streams(path: Path) -> list[str]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return sorted(line.strip().strip(",") for line in out.splitlines() if line.strip())


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


@pytest.fixture
def downloader(tmp_path: Path) -> VideoDownloader:
    return VideoDownloader(download_dir=str(tmp_path / "dl"), max_download_size_bytes=50 * 1024 * 1024)


@pytest.fixture
def silent_video(tmp_path: Path) -> Path:
    path = tmp_path / "silent.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=4:size=160x120:rate=10", "-pix_fmt", "yuv420p", str(path))
    return path


@pytest.fixture
def music(tmp_path: Path) -> dict:
    path = tmp_path / "music.m4a"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=20", "-c:a", "aac", str(path))
    return {"audio_url": path.as_uri(), "audio_timestamps": [5000, 1000]}


def test_split_music_item_separates_audio_track():
    image = {"num": 1, "display_url": "https://x/1.jpg", "video_url": None, "audio_url": None}
    video = {"num": 2, "display_url": "https://x/2.jpg", "video_url": "https://x/2.mp4"}
    track = {"num": 3, "display_url": "https://x/cover.jpg", "audio_url": "https://x/a.mp4"}

    media, music_item = split_music_item([image, video, track])

    assert media == [image, video]
    assert music_item is track


def test_split_music_item_without_audio_track():
    video = {"num": 1, "video_url": "https://x/1.mp4"}
    assert split_music_item([video]) == ([video], None)


def test_silent_video_gets_music_track(downloader, silent_video, music):
    assert _streams(silent_video) == ["video"]

    downloader._add_music_if_silent(silent_video, music)

    assert _streams(silent_video) == ["audio", "video"]
    # Die Musik ist laenger als das Video; die Videolaenge bleibt massgeblich.
    assert _duration(silent_video) == pytest.approx(4.0, abs=0.5)


def test_video_longer_than_remaining_music_keeps_its_length(downloader, silent_video, music):
    # Ab 18 s bleiben nur 2 s Musik fuer 4 s Video.
    music["audio_timestamps"] = [18000]

    downloader._add_music_if_silent(silent_video, music)

    assert _streams(silent_video) == ["audio", "video"]
    assert _duration(silent_video) == pytest.approx(4.0, abs=0.5)


def test_video_with_own_audio_is_left_untouched(downloader, tmp_path, music):
    path = tmp_path / "loud.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
        "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
    )
    before = path.read_bytes()

    downloader._add_music_if_silent(path, music)

    assert path.read_bytes() == before


def test_failed_music_download_keeps_silent_video(downloader, silent_video, tmp_path):
    before = silent_video.read_bytes()

    downloader._add_music_if_silent(silent_video, {"audio_url": (tmp_path / "missing.m4a").as_uri()})

    assert silent_video.read_bytes() == before
