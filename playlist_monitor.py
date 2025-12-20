import os
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "user-read-currently-playing user-read-playback-state"

LAST_PLAYLIST_FILE = "last_playlist.txt"

def get_last_playlist():
    if not os.path.exists(LAST_PLAYLIST_FILE):
        return None
    with open(LAST_PLAYLIST_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None

def save_last_playlist(name):
    with open(LAST_PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(name)

def main():
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            cache_path=".cache",
            open_browser=False
        )
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    current = sp.current_user_playing_track()
    if not current or not current.get("context"):
        print(f"[{now}] No hay playlist activa.")
        return

    if current["context"]["type"] != "playlist":
        print(f"[{now}] Reproduciendo pero no desde playlist.")
        return

    playlist_id = current["context"]["uri"].split(":")[-1]
    playlist_name = sp.playlist(playlist_id)["name"]

    last_playlist = get_last_playlist()

    if playlist_name == last_playlist:
        print(f"[{now}] Playlist sin cambios: {playlist_name}")
        return

    print(f"[{now}] CAMBIO DETECTADO → {playlist_name}")
    save_last_playlist(playlist_name)

if __name__ == "__main__":
    main()

