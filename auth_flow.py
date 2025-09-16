import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

# Initialize Spotify OAuth with write permissions
sp_oauth = SpotifyOAuth(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    redirect_uri=os.getenv('REDIRECT_URI'),
    scope='playlist-modify-public playlist-modify-private user-read-private',
    cache_handler=spotipy.cache_handler.MemoryCacheHandler()
)

# Get authorization URL and prompt user to visit it
auth_url = sp_oauth.get_authorize_url()
print(f"Please visit this URL to authorize the application: {auth_url}")

# After authorization, the user will be redirected to the redirect_uri
# You'll need to paste the full redirect URL here
response_url = input("Paste the redirect URL here: ")
code = sp_oauth.parse_response_code(response_url)
token_info = sp_oauth.get_access_token(code)

# Print the refresh token to use in production
print(f"\nRefresh token: {token_info['refresh_token']}")
print("Add this to your .env file as REFRESH_TOKEN")
