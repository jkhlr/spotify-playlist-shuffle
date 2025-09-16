import os
import random
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


class PlaylistShuffleError(Exception):
    """Raised when shuffling a playlist fails."""
    pass


class PlaylistRestoreError(Exception):
    """Raised when restoring a playlist fails after a shuffle error."""
    def __init__(self, restore_error, shuffle_error):
        self.restore_error = restore_error
        self.shuffle_error = shuffle_error
        super().__init__(
            f"Failed to restore playlist after shuffle error.\n"
            f"Shuffle error: {shuffle_error}\n"
            f"Restore error: {restore_error}"
        )


def get_spotify_client():
    """Initialize and return a Spotify client using a refresh token.

    In serverless environments we cannot perform the interactive OAuth flow,
    so we rely on a pre‑generated ``REFRESH_TOKEN`` stored in the environment.
    The token is exchanged for a fresh access token, which is then used to
    instantiate a Spotipy client.
    """
    # Basic OAuth configuration – required for token refresh.
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        redirect_uri=os.getenv('REDIRECT_URI'),
        scope='playlist-modify-public playlist-modify-private user-read-private',
        cache_handler=spotipy.cache_handler.MemoryCacheHandler()
    )

    refresh_token = os.getenv('REFRESH_TOKEN')
    if not refresh_token:
        raise RuntimeError(
            "REFRESH_TOKEN not found in environment. "
            "Set the REFRESH_TOKEN variable to a valid Spotify refresh token."
        )

    # Exchange the refresh token for a new access token.
    token_info = sp_oauth.refresh_access_token(refresh_token)
    access_token = token_info.get('access_token')
    if not access_token:
        raise RuntimeError("Failed to obtain an access token using the refresh token.")

    # Return a Spotipy client authenticated with the fresh access token.
    return spotipy.Spotify(auth=access_token)


def update_playlist_tracks(sp, playlist_id, track_uris):
    """Replace all tracks in a playlist with the given track URIs.

    Args:
        sp: Spotify client instance
        playlist_id: ID of the playlist to update
        track_uris: List of Spotify track URIs
    """
    sp.playlist_replace_items(playlist_id, [])
    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i:i+100])


def shuffle_playlist_tracks(playlist_id):
    """Shuffle tracks in a Spotify playlist."""
    sp = get_spotify_client()

    # Get current tracks
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    if not tracks:
        return "Playlist is empty"

    # Extract track URIs and create backup
    original_track_uris = [item['track']['uri'] for item in tracks]
    shuffled_track_uris = original_track_uris.copy()
    random.shuffle(shuffled_track_uris)

    try:
        update_playlist_tracks(sp, playlist_id, shuffled_track_uris)
    except Exception as shuffle_error:
        # On any failure, attempt to restore original playlist
        try:
            update_playlist_tracks(sp, playlist_id, original_track_uris)
        except Exception as restore_error:
            raise PlaylistRestoreError(restore_error, shuffle_error) from restore_error

        raise PlaylistShuffleError("Failed to shuffle playlist") from shuffle_error

    return f"Shuffled {len(shuffled_track_uris)} tracks in playlist {playlist_id}"

if __name__ == "__main__":
    playlist_id = os.getenv('PLAYLIST_ID')
    shuffle_playlist_tracks(playlist_id)