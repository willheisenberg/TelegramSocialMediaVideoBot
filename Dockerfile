FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# JavaScript-Runtime fuer yt-dlp. YouTube verschluesselt die Format-URLs mit einer
# in JS ausgelieferten Signatur (nsig); ohne Runtime kann yt-dlp sie nicht loesen
# und faellt auf Player-Clients zurueck, deren URLs YouTube mangels PO-Token mit
# HTTP 403 abweist. Deno ist die von yt-dlp standardmaessig unterstuetzte Runtime.
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh -s -- -y

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# yt-dlp/gallery-dl brechen bei jeder YouTube-/Plattform-Aenderung; deshalb bei
# jedem Build die neueste Version ziehen. CACHE_BUST (vom deploy.sh mit einem
# Zeitstempel gesetzt) invalidiert diese Layer bei jedem Deploy erneut, sonst
# wuerde Docker den Upgrade-Schritt cachen und wieder eine alte Version behalten.
ARG CACHE_BUST=unknown
RUN pip install --no-cache-dir --upgrade yt-dlp gallery-dl

COPY app ./app
COPY main.py .

CMD ["python", "main.py"]
