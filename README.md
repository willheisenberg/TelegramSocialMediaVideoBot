# Telegram Social Media Video Bot

Ein Telegram-Bot, der Videos, GIFs, Bilder und vollständige Galerien aus unterstützten Social-Media-Plattformen herunterlädt und direkt im Telegram-Chat zurücksendet. 

Durch die nahtlose Integration von `yt-dlp` und `gallery-dl` werden auch passwortgeschützte oder blockierte Plattformen und komplexe Multi-Image/Video-Carousels (wie von Instagram, Reddit, X/Twitter und TikTok) zuverlässig verarbeitet.

---

## Hauptfunktionen

- **Automatisierte Videodownloads:** Lädt Videos von allen von `yt-dlp` unterstützten Plattformen herunter (YouTube, TikTok, X, etc.).
- **Zuverlässige Galerie- & Carousel-Downloads (`gallery-dl`):** Erkennt automatisch Bild- und Video-Carousels (z. B. Instagram-Slides) und lädt alle Medien herunter.
- **Native Telegram-Alben (Media Groups):** Sendet mehrteilige Galerien als ein elegantes, zusammenhängendes Album mit Originalbeschreibung zurück (unterstützt gemischte Fotos & Videos).
- **Gezielte Bildauswahl (`img_index`):** Durch Anhängen von z. B. `?img_index=8` an eine Instagram-URL wird gezielt nur das 8. Element der Galerie heruntergeladen.
- **Direkt-Image & GIF Downloads:** Erkennt direkte Bildlinks und sendet diese sofort als Foto oder als voll-animiertes GIF.
- **Universal-Cookies & Plattform-Credentials:**
  - Automatische Erkennung einer `cookies.txt` (Netscape-Format) im Stammverzeichnis für universellen Session-Zugriff.
  - Dynamisches Routing von plattformspezifischen Zugangsdaten (Instagram, YouTube, Twitter, TikTok) direkt über die `.env`-Konfiguration.

---

## Voraussetzungen

- Ein Telegram-Bot-Token von `@BotFather`
- **Für Docker:** Docker und Docker Compose
- **Für lokale Ausführung:** Python 3.10+ und ein virtuelles Environment (`venv`)

---

## Konfiguration

1. Beispieldatei kopieren:
   ```bash
   cp .env.example .env
   ```

2. `.env` anpassen und deine Werte eintragen:
   - `TELEGRAM_BOT_TOKEN`: Dein Bot-Token.
   - `COOKIES_FILE_PATH`: (Optional) Pfad zu deiner `cookies.txt`. Wenn leer gelassen, sucht der Bot automatisch im Projektstamm nach einer Datei namens `cookies.txt`.
   - **Plattformspezifische Logins:** Setze Passwörter und Benutzernamen für Instagram, YouTube, Twitter und TikTok direkt in die jeweiligen Felder ein.

3. **Session-Cookies hinterlegen (Empfohlen für Instagram):**
   - Exportiere deine Instagram-Cookies im Netscape-Format und speichere sie als `cookies.txt` im Projektverzeichnis ab (diese Datei ist in `.gitignore` eingetragen und bleibt geschützt).

---

## Starten des Bots

### Methode A: Lokale Ausführung (venv)
1. Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
3. Bot starten:
   ```bash
   python3 main.py
   ```

### Methode B: Docker & Docker Compose
Starten im Hintergrund:
```bash
docker compose up --build -d
```

Logs ansehen:
```bash
docker compose logs -f
```

---

## Nutzung im Chat

- **Ein einzelnes Video/Bild laden:** Sende einfach den Link an den Bot. Er lädt die Datei und sendet sie als Video, GIF oder Foto zurück.
- **Eine ganze Galerie laden:** Sende den Link zu einem Slider-Post (z. B. von Instagram). Der Bot lädt alle Bilder/Videos herunter und schickt sie als Album.
- **Ein bestimmtes Bild aus der Galerie laden:** Hänge einfach den URL-Parameter an (z. B. `https://www.instagram.com/p/.../?img_index=3`). Der Bot lädt nur das 3. Bild.

---

## Hinweise & Limits

- **Telegram-Größenlimit:** Standardmäßig auf `49 MB` gesetzt, damit Uploads über den Bot flüssig und zuverlässig bleiben (über `MAX_DOWNLOAD_SIZE_BYTES` konfigurierbar).
- **Plattformänderungen:** Da Social-Media-Seiten stetig ihr Layout oder APIs anpassen, nutzt der Bot standardmäßig die aktuellsten Versionen von `yt-dlp` und `gallery-dl`.
