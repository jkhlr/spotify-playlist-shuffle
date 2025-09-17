import argparse
import os
import random
from functools import cached_property
from pprint import pprint

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()


class PlaylistShuffleError(Exception):
    """Raised when shuffling a playlist fails."""
    pass


class PlaylistRestoreError(Exception):
    """Raised when restoring a playlist fails after a shuffle error."""

    def __init__(self, restore_error, shuffle_error):
        self.restore_error = restore_error
        self.shuffle_error = shuffle_error
        super().__init__(f"Failed to restore playlist after shuffle error.\n"
                         f"Restore error: {restore_error}\n"
                         f"Shuffle error: {shuffle_error}")


class SpotifyClient:
    """Client for interacting with Spotify API."""
    
    @cached_property
    def spotify(self):
        """Initialize the Spotify client using a refresh token."""
        # Basic OAuth configuration – required for token refresh.
        sp_oauth = SpotifyOAuth(client_id=os.getenv('CLIENT_ID'), client_secret=os.getenv('CLIENT_SECRET'),
                                redirect_uri=os.getenv('REDIRECT_URI'),
                                scope='playlist-modify-public playlist-modify-private user-read-private',
                                cache_handler=spotipy.cache_handler.MemoryCacheHandler())
        
        refresh_token = os.getenv('REFRESH_TOKEN')
        if not refresh_token:
            raise RuntimeError("REFRESH_TOKEN not found in environment. "
                               "Set the REFRESH_TOKEN variable to a valid Spotify refresh token.")
        
        # Exchange the refresh token for a new access token.
        token_info = sp_oauth.refresh_access_token(refresh_token)
        access_token = token_info.get('access_token')
        if not access_token:
            raise RuntimeError("Failed to obtain an access token using the refresh token.")
        
        # Store Spotipy client authenticated with the fresh access token.
        return spotipy.Spotify(auth=access_token)

    def get_playlists(self):
        """Get a list of all playlists owned by the authenticated user."""
        user = self.spotify.current_user()
        results = self.spotify.current_user_playlists()
        playlists = results['items']
        while results['next']:
            results = self.spotify.next(results)
            playlists.extend(results['items'])
        return [playlist for playlist in playlists if playlist['owner']['id'] == user['id']]

    def update_playlist_tracks(self, playlist_id, track_uris):
        """Replace all tracks in a playlist with the given track URIs.

        Args:
            playlist_id: ID of the playlist to update
            track_uris: List of Spotify track URIs
        """
        self.spotify.playlist_replace_items(playlist_id, [])
        for i in range(0, len(track_uris), 100):
            self.spotify.playlist_add_items(playlist_id, track_uris[i:i + 100])

    def shuffle_playlist_tracks(self, playlist_id):
        """Shuffle tracks in a Spotify playlist."""
        # Get current tracks
        results = self.spotify.playlist_tracks(playlist_id)
        tracks = results['items']
        while results['next']:
            results = self.spotify.next(results)
            tracks.extend(results['items'])

        if not tracks:
            return "Playlist is empty"

        # Extract track URIs and create backup
        original_track_uris = [item['track']['uri'] for item in tracks]
        shuffled_track_uris = original_track_uris.copy()
        random.shuffle(shuffled_track_uris)

        try:
            self.update_playlist_tracks(playlist_id, shuffled_track_uris)
        except Exception as shuffle_error:
            # On any failure, attempt to restore original playlist
            try:
                self.update_playlist_tracks(playlist_id, original_track_uris)
            except Exception as restore_error:
                raise PlaylistRestoreError(restore_error, shuffle_error) from restore_error

            raise PlaylistShuffleError("Failed to shuffle playlist") from shuffle_error

        return f"Shuffled {len(shuffled_track_uris)} tracks in playlist {playlist_id}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shuffle", type=str)
    args = parser.parse_args()

    client = SpotifyClient()
    if args.shuffle:
        playlist_id = args.shuffle
        print(client.shuffle_playlist_tracks(playlist_id))
    else:
        playlists = client.get_playlists()
        pprint([
            {
                'name': playlist['name'],
                'id': playlist['id']
            }
            for playlist in playlists
        ])

if __name__ == "__main__":
    main()
    