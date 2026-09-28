import pytest

from app.url_filter import is_supported_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/shorts/abc123",
        "https://www.instagram.com/p/ABC/?img_index=3",
        "https://www.tiktok.com/@user/video/123",
        "https://vm.tiktok.com/ZMabc/",
        "https://x.com/user/status/123",
        "https://twitter.com/user/status/123",
        "https://www.reddit.com/r/videos/comments/abc/title/",
        "https://v.redd.it/abc123",
        "https://vimeo.com/123456",
        "https://www.facebook.com/watch/?v=123",
        "https://example.com/bild.JPG",
        "https://cdn.example.org/clip.mp4?token=1",
    ],
)
def test_supported_urls(url):
    assert is_supported_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.kino.de/film/irgendein-film-2026/",
        "https://www.cinemaxx.de/kinoprogramm/berlin",
        "https://www.spiegel.de/politik/artikel-123.html",
        "https://www.amazon.de/dp/B000000",
        "https://notyoutube.com/watch?v=abc",
        "https://youtube.com.evil.example/watch?v=abc",
        "http://",
    ],
)
def test_unsupported_urls(url):
    assert not is_supported_url(url)
