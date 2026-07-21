"""Print the Spotify authorization URL.

Uses CLIENT_ID / CLIENT_SECRET / REDIRECT_URI from the environment (or a local
.env file) to build the OAuth authorization URL. Visit the printed URL in a
browser, approve access, and copy the URL you get redirected to. Feed that
redirect URL into ``update_refresh_token.py`` to mint a new refresh token.
"""

import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# Scope kept in sync with spotify_client.py.
SCOPE = "playlist-modify-public playlist-modify-private user-read-private"


def build_auth_url():
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        redirect_uri=os.getenv("REDIRECT_URI"),
        scope=SCOPE,
        cache_handler=spotipy.cache_handler.MemoryCacheHandler(),
    )
    return sp_oauth.get_authorize_url()


if __name__ == "__main__":
    print(build_auth_url())
