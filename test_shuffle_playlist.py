import pytest
from unittest.mock import MagicMock
from shuffle_playlist import (
    PlaylistShuffleError,
    PlaylistRestoreError,
    shuffle_playlist_tracks,
    update_playlist_tracks
)

@pytest.fixture
def mock_spotify_client(monkeypatch):
    """Fixture that provides a mocked Spotify client."""
    mock_client = MagicMock()

    # Mock playlist_tracks response
    mock_client.playlist_tracks.return_value = {
        'items': [
            {'track': {'uri': f'spotify:track:{i}'}} for i in range(5)
        ],
        'next': None
    }

    # Mock get_spotify_client to return our mock
    monkeypatch.setattr('shuffle_playlist.get_spotify_client', lambda: mock_client)
    return mock_client

def test_shuffle_failure_with_successful_restore(mock_spotify_client, monkeypatch):
    """Test that when shuffle fails but restore succeeds, we get a PlaylistShuffleError."""

    call_count = 0
    def mock_update_that_fails_once(sp, playlist_id, track_uris):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Simulated shuffle failure")
        # Second call (restore) succeeds

    monkeypatch.setattr('shuffle_playlist.update_playlist_tracks', mock_update_that_fails_once)

    with pytest.raises(PlaylistShuffleError) as exc_info:
        shuffle_playlist_tracks("test_playlist_id")

    assert "Failed to shuffle playlist" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "Simulated shuffle failure"
    assert call_count == 2  # Should be called twice: once for shuffle (fails) and once for restore (succeeds)

def test_both_shuffle_and_restore_failure(mock_spotify_client, monkeypatch):
    """Test that when both shuffle and restore fail, we get a PlaylistRestoreError."""

    def mock_update_that_always_fails(sp, playlist_id, track_uris):
        raise ValueError("Simulated failure")

    monkeypatch.setattr('shuffle_playlist.update_playlist_tracks', mock_update_that_always_fails)

    with pytest.raises(PlaylistRestoreError) as exc_info:
        shuffle_playlist_tracks("test_playlist_id")

    error = exc_info.value
    assert isinstance(error.shuffle_error, ValueError)
    assert isinstance(error.restore_error, ValueError)
    assert "Simulated failure" in str(error.shuffle_error)
    assert "Simulated failure" in str(error.restore_error)

def test_empty_playlist(mock_spotify_client):
    """Test handling of empty playlists."""
    # Override the mock to return an empty playlist
    mock_spotify_client.playlist_tracks.return_value = {
        'items': [],
        'next': None
    }

    result = shuffle_playlist_tracks("test_playlist_id")
    assert result == "Playlist is empty"
