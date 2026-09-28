from __future__ import annotations

import urllib.parse

# Plattformen, fuer die der Bot Links annimmt. Verglichen wird per Domain-Suffix,
# d.h. "youtube.com" deckt auch "www.youtube.com" und "m.youtube.com" ab.
# Alle anderen Links (Nachrichtenseiten, Kino-Seiten, Shops, ...) werden ignoriert,
# statt dass yt-dlp versucht, aus beliebigem HTML etwas herunterzuladen.
ALLOWED_DOMAINS: frozenset[str] = frozenset(
    {
        # YouTube
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        # Meta
        "instagram.com",
        "facebook.com",
        "fb.watch",
        "fb.com",
        "threads.net",
        "threads.com",
        # X / Twitter
        "twitter.com",
        "x.com",
        "fxtwitter.com",
        "vxtwitter.com",
        "fixupx.com",
        # TikTok
        "tiktok.com",
        # Reddit
        "reddit.com",
        "redd.it",
        # Weitere Video-/Social-Plattformen
        "vimeo.com",
        "dailymotion.com",
        "dai.ly",
        "twitch.tv",
        "streamable.com",
        "pinterest.com",
        "pin.it",
        "snapchat.com",
        "linkedin.com",
        "tumblr.com",
        "bsky.app",
        "9gag.com",
        "imgur.com",
        "giphy.com",
        "tenor.com",
        "kick.com",
        "rumble.com",
        "bilibili.com",
        "vk.com",
        "ok.ru",
        "soundcloud.com",
    }
)

# Direktlinks auf Mediendateien bleiben unabhaengig von der Domain erlaubt.
DIRECT_MEDIA_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".heic",
    ".heif",
    ".gif",
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
)


def _host(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return ""
    return host.lower().rstrip(".")


def is_allowed_domain(host: str) -> bool:
    """True, wenn ``host`` eine erlaubte Domain oder deren Subdomain ist."""
    return any(host == domain or host.endswith("." + domain) for domain in ALLOWED_DOMAINS)


def is_supported_url(url: str) -> bool:
    """Entscheidet, ob der Bot fuer ``url`` einen Download versuchen soll.

    Erlaubt sind bekannte Social-Media-/Video-Plattformen sowie Direktlinks auf
    Bild- und Videodateien. Alles andere wird abgelehnt.
    """
    host = _host(url)
    if not host:
        return False
    if is_allowed_domain(host):
        return True
    try:
        path = urllib.parse.urlparse(url).path.lower()
    except ValueError:
        return False
    return path.endswith(DIRECT_MEDIA_EXTENSIONS)
