import os
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "user-read-currently-playing user-read-playback-state"

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]

LAST_STATE_FILE = "last_state.txt"


def get_last_state():
    if not os.path.exists(LAST_STATE_FILE):
        return None
    with open(LAST_STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def save_last_state(value: str):
    with open(LAST_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(value or "")


def send_email(subject: str, body: str):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            cache_path=".cache",
            open_browser=False,
        )
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    current = sp.current_user_playing_track()
    if not current or not current.get("item"):
        print(f"[{now}] No hay reproducción activa.")
        return

    item = current["item"]
    track_name = item.get("name", "Unknown track")
    artists = ", ".join(
        a.get("name", "") for a in item.get("artists", []) if a.get("name")
    ) or "Unknown artist"

    context = current.get("context")
    last_state = get_last_state()

    # --- CASO 1: SIN CONTEXT ---
    if not context:
        track_id = item.get("id") or track_name
        state_key = f"no_context|track:{track_id}"

        if state_key == last_state:
            print(f"[{now}] Sin cambios (sin context).")
            return

        subject = "[Spotify] Reproducción (sin playlist)"
        body = (
            f"Hora: {now}\n"
            f"Spotify no devolvió 'context' (no se puede saber si es playlist/álbum).\n"
            f"Canción: {track_name}\n"
            f"Artista(s): {artists}\n"
        )

        send_email(subject, body)
        save_last_state(state_key)
        print(f"[{now}] Notificación enviada (sin context).")
        return

    ctype = context.get("type")
    uri = context.get("uri") or ""

    # --- CASO 2: ES PLAYLIST ---
    if ctype == "playlist" and uri:
        # Usamos URI como identificador estable (evita 404 por playlist_id mal parseado)
        state_key = f"playlist|{uri}"

        # DEBUG (dejalo mientras probamos)
        print(f"[{now}] DEBUG last_state={last_state}")
        print(f"[{now}] DEBUG state_key={state_key}")

        if state_key == last_state:
            print(f"[{now}] Sin cambios: Playlist {uri}")
            return

        # Intentamos obtener nombre (si falla, usamos el URI)
        playlist_name = uri
        try:
            playlist_id = uri.split(":")[-1]
            playlist = sp.playlist(playlist_id)
            playlist_name = playlist.get("name") or uri
        except Exception as e:
            print(f"[{now}] No pude resolver nombre de playlist (uso URI). Motivo: {e}")

        subject = "[Spotify] Cambio de playlist"
        body = (
            f"Hora: {now}\n"
            f"Playlist: {playlist_name}\n"
            f"URI: {uri}\n"
            f"Canción: {track_name}\n"
            f"Artista(s): {artists}\n"
        )

        send_email(subject, body)
        save_last_state(state_key)
        print(f"[{now}] Notificación enviada: Playlist {playlist_name}")
        return

    # --- CASO 3: NO ES PLAYLIST (álbum, radio, artista, etc.) ---
    stable_id = uri or (item.get("id") or track_name)
    state_key = f"not_playlist|{ctype}|{stable_id}"

    if state_key == last_state:
        print(f"[{now}] Sin cambios: No-playlist ({ctype})")
        return

    source_label = f"Origen: {ctype}"
    if ctype == "album":
        album_name = (item.get("album") or {}).get("name")
        if album_name:
            source_label = f"Álbum: {album_name}"

    subject = "[Spotify] Reproducción fuera de playlist"
    body = (
        f"Hora: {now}\n"
        f"{source_label}\n"
        f"Canción: {track_name}\n"
        f"Artista(s): {artists}\n"
        f"URI: {uri}\n"
    )

    send_email(subject, body)
    save_last_state(state_key)
    print(f"[{now}] Notificación enviada: fuera de playlist ({ctype})")


if __name__ == "__main__":
    main()
