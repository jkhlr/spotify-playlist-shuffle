from django.shortcuts import render
from spotify_api.spotify_client import SpotifyClient


def index(request):
    client = SpotifyClient()
    playlists = client.get_playlists()
    return render(request, 'shuffle/index.html', {'playlists': playlists})
