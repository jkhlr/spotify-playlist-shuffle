import pytest
from unittest.mock import MagicMock
from spotify_api.spotify_client import (
    PlaylistShuffleError,
    PlaylistRestoreError,
    SpotifyClient
)

@pytest.fixture
def mock_spotify_client(monkeypatch):
    """Fixture that provides a mocked SpotifyClient."""
    client = SpotifyClient()
    client.spotify = MagicMock()

    # Mock playlist_tracks response
    client.spotify.playlist_tracks.return_value = {
        'items': [
            {'track': {'uri': f'spotify:track:{i}'}} for i in range(5)
        ],
        'next': None
    }

    return client


def test_shuffle_failure_with_successful_restore(mock_spotify_client):
    """Test that when shuffle fails but restore succeeds, we get a PlaylistShuffleError."""
    call_count = 0

    def mock_update_that_fails_once(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Simulated shuffle failure")
        # Second call (restore) succeeds

    mock_spotify_client.update_playlist_tracks = mock_update_that_fails_once

    with pytest.raises(PlaylistShuffleError) as exc_info:
        mock_spotify_client.shuffle_playlist_tracks("test_playlist_id")

    assert "Failed to shuffle playlist" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "Simulated shuffle failure"
    assert call_count == 2  # Should be called twice: once for shuffle (fails) and once for restore (succeeds)

def test_both_shuffle_and_restore_failure(mock_spotify_client):
    """Test that when both shuffle and restore fail, we get a PlaylistRestoreError."""

    def mock_update_that_always_fails(*args, **kwargs):
        raise ValueError("Simulated failure")

    mock_spotify_client.update_playlist_tracks = mock_update_that_always_fails

    with pytest.raises(PlaylistRestoreError) as exc_info:
        mock_spotify_client.shuffle_playlist_tracks("test_playlist_id")

    error = exc_info.value
    assert isinstance(error.shuffle_error, ValueError)
    assert isinstance(error.restore_error, ValueError)
    assert "Simulated failure" in str(error.shuffle_error)
    assert "Simulated failure" in str(error.restore_error)

def test_empty_playlist(mock_spotify_client):
    """Test handling of empty playlists."""
    # Override the mock to return an empty playlist
    mock_spotify_client.spotify.playlist_tracks.return_value = {
        'items': [],
        'next': None
    }

    result = mock_spotify_client.shuffle_playlist_tracks("test_playlist_id")
    assert result == "Playlist is empty"


def test_get_playlists(mock_spotify_client):
    """Test getting user playlists."""
    mock_spotify_client.spotify.current_user.return_value = {'id': 'test_user'}
    mock_spotify_client.spotify.current_user_playlists.return_value = {
        'items': [
            {'name': 'Playlist 1', 'id': '1', 'owner': {'id': 'test_user'}},
            {'name': 'Playlist 2', 'id': '2', 'owner': {'id': 'other_user'}},
        ],
        'next': None
    }

    playlists = mock_spotify_client.get_playlists()
    assert len(playlists) == 1
    assert playlists[0]['name'] == 'Playlist 1'
    assert playlists[0]['id'] == '1'
