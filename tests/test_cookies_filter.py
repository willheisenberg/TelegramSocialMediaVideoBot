from datetime import datetime, timezone

import pytest
from telegram import Animation, Chat, Document, Message, Update

from app.bot import COOKIES_DOCUMENT_FILTER

CHAT = Chat(id=1, type="group")


def _update(**kwargs) -> Update:
    message = Message(message_id=1, date=datetime.now(timezone.utc), chat=CHAT, **kwargs)
    return Update(update_id=1, message=message)


def _document(file_name: str | None, mime_type: str | None) -> Document:
    return Document(file_id="f", file_unique_id="u", file_name=file_name, mime_type=mime_type)


@pytest.mark.parametrize(
    ("file_name", "mime_type"),
    [
        ("cookies.txt", "text/plain"),
        ("cookies.TXT", None),
        ("export", "text/plain"),
    ],
)
def test_accepts_text_files(file_name, mime_type):
    assert COOKIES_DOCUMENT_FILTER.check_update(_update(document=_document(file_name, mime_type)))


@pytest.mark.parametrize(
    ("file_name", "mime_type"),
    [
        ("bericht.pdf", "application/pdf"),
        ("bild.png", "image/png"),
        ("clip.mp4", "video/mp4"),
        (None, None),
    ],
)
def test_ignores_other_documents(file_name, mime_type):
    assert not COOKIES_DOCUMENT_FILTER.check_update(_update(document=_document(file_name, mime_type)))


def test_ignores_gif_animation():
    animation = Animation(
        file_id="a", file_unique_id="a", width=1, height=1, duration=1,
        file_name="living_the_dream.mp4", mime_type="video/mp4",
    )
    # Telegram liefert bei GIFs sowohl `animation` als auch `document`.
    update = _update(animation=animation, document=_document("living_the_dream.mp4", "video/mp4"))
    assert not COOKIES_DOCUMENT_FILTER.check_update(update)
