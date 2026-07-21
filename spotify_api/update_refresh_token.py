"""Exchange a Spotify redirect URL for a refresh token and store it as a secret.

Given the URL you were redirected to after approving access (contains a
``?code=...`` query parameter), this:

1. Exchanges the authorization code for a fresh Spotify refresh token.
2. Encrypts that token with the repository's Actions public key.
3. Writes it to the ``REFRESH_TOKEN`` repository secret via the GitHub REST API.

Required environment variables:
    CLIENT_ID, CLIENT_SECRET, REDIRECT_URI  Spotify app credentials.
    REDIRECT_URL                            The full URL you were redirected to.
    GITHUB_REPOSITORY                        "owner/repo" (set by GitHub Actions).
    GH_PAT                                   A token allowed to write secrets
                                             (fine-grained PAT with "Secrets"
                                             read/write, or classic PAT with the
                                             "repo" scope). The default
                                             GITHUB_TOKEN is NOT sufficient.

The refresh token itself is never printed.
"""

import os
import sys
from base64 import b64encode

import requests
import spotipy
from dotenv import load_dotenv
from nacl import encoding, public
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPE = "playlist-modify-public playlist-modify-private user-read-private"
SECRET_NAME = "REFRESH_TOKEN"
API_VERSION = "2022-11-28"


def _require(name):
    value = os.getenv(name)
    if not value:
        sys.exit(f"Error: environment variable {name} is required but not set.")
    return value


def exchange_code_for_refresh_token(redirect_url):
    sp_oauth = SpotifyOAuth(
        client_id=_require("CLIENT_ID"),
        client_secret=_require("CLIENT_SECRET"),
        redirect_uri=_require("REDIRECT_URI"),
        scope=SCOPE,
        cache_handler=spotipy.cache_handler.MemoryCacheHandler(),
    )
    code = sp_oauth.parse_response_code(redirect_url)
    if not code or code == redirect_url:
        sys.exit(
            "Error: could not find an authorization code in REDIRECT_URL. "
            "Make sure you pasted the full URL you were redirected to "
            "(it contains '?code=...')."
        )
    token_info = sp_oauth.get_access_token(code, as_dict=True, check_cache=False)
    refresh_token = token_info.get("refresh_token")
    if not refresh_token:
        sys.exit("Error: Spotify did not return a refresh token.")
    return refresh_token


def _encrypt_secret(public_key_b64, secret_value):
    """Encrypt a value using a repository's Actions public key (libsodium sealed box)."""
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def update_repo_secret(refresh_token):
    repo = _require("GITHUB_REPOSITORY")
    token = _require("GH_PAT")
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    })

    key_resp = session.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    )
    if key_resp.status_code != 200:
        sys.exit(
            f"Error fetching repo public key ({key_resp.status_code}): {key_resp.text}\n"
            "Check that GH_PAT is valid and has permission to write Actions secrets."
        )
    key_data = key_resp.json()

    encrypted_value = _encrypt_secret(key_data["key"], refresh_token)

    put_resp = session.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{SECRET_NAME}",
        json={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
    )
    if put_resp.status_code not in (201, 204):
        sys.exit(
            f"Error updating secret {SECRET_NAME} ({put_resp.status_code}): {put_resp.text}"
        )


def main():
    redirect_url = _require("REDIRECT_URL")
    refresh_token = exchange_code_for_refresh_token(redirect_url)
    update_repo_secret(refresh_token)
    print(f"Successfully updated the {SECRET_NAME} secret.")


if __name__ == "__main__":
    main()
