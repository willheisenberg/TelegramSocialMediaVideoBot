# Telegram Social Media Video Bot

Ein Telegram-Bot, der Videolinks aus unterstuetzten Social-Media-Plattformen mit `yt-dlp` herunterlaedt und das Video direkt im Telegram-Chat zuruecksenden kann.

## Funktionsumfang

- Telegram-Bot per Long Polling
- Download von Videolinks, die `yt-dlp` unterstuetzt
- Docker-Image und Deployment via `docker compose`
- Groessenlimit ueber Umgebungsvariable steuerbar

## Voraussetzungen

- Ein Telegram-Bot-Token von `@BotFather`
- Docker und Docker Compose

## Konfiguration

1. Beispieldatei kopieren:

```bash
cp .env.example .env
```

2. In `.env` den Wert fuer `TELEGRAM_BOT_TOKEN` setzen.

## Start

```bash
docker compose up --build -d
```

Logs ansehen:

```bash
docker compose logs -f
```

## Nutzung

- Dem Bot einen Link zu einem Video senden
- Der Bot versucht, das Video herunterzuladen und als Telegram-Video zurueckzusenden

## Hinweise

- Welche Plattformen konkret funktionieren, haengt von `yt-dlp` und den jeweiligen Plattformaenderungen ab.
- Manche Plattformen beschraenken oder blockieren Downloads technisch oder rechtlich.
- Das Standardlimit ist auf `49 MB` gesetzt, damit Uploads ueber den Bot praktikabel bleiben.
