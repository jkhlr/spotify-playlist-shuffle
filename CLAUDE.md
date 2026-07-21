# CLAUDE.md

Guidance for working in this repository.

## Project overview

A Spotify playlist shuffler. `spotify_api/spotify_client.py` authenticates with
Spotify using a stored refresh token and reshuffles a playlist. It runs daily
via the **Daily Spotify Shuffle** GitHub Actions workflow
(`.github/workflows/daily-shuffle.yml`, cron `0 6 * * *`).

Dependencies are managed with `uv`; run things with `uv run` (e.g.
`uv run pytest`, `uv run python spotify_api/spotify_client.py`).

## Spotify authentication

The daily job authenticates by exchanging a long-lived **refresh token** for a
short-lived access token. Credentials live in GitHub Actions, not in the repo:

- Variables (`vars.*`): `CLIENT_ID`, `REDIRECT_URI`, `PLAYLIST_ID`
- Secrets (`secrets.*`): `CLIENT_SECRET`, `REFRESH_TOKEN`, `GH_PAT`

Locally, the same values can be provided via a `.env` file (gitignored); see
`load_dotenv()` usage in the scripts.

### Redirect URI requirement

Spotify no longer accepts `http://localhost/` as a redirect URI ("insecure"
error). Loopback redirect URIs must use the explicit IP with a port, e.g.
`http://127.0.0.1:8888/callback`. This exact value must be:

1. Registered in the Spotify app settings (developer dashboard), and
2. Stored in the `REDIRECT_URI` repository variable.

Note: token *refresh* does not send the redirect URI, so the daily job keeps
working even if it drifts — but the auth flow below needs it to match.

## Refreshing the Spotify refresh token (the common CI failure)

**Symptom:** the Daily Spotify Shuffle job fails with
`SpotifyOauthError: error: invalid_grant, error_description: Refresh token expired`
(raised from `refresh_access_token` in `spotify_client.py`). This is a
credentials problem, not a code bug — the `REFRESH_TOKEN` secret must be
renewed. Do NOT change code to "fix" it.

The renewal is fully automated via two manually-triggered workflows, so it can
be done entirely from GitHub Actions without visiting the Spotify dashboard or
handling `CLIENT_SECRET` locally. These can be dispatched via the GitHub API
(`run_workflow` on `main`), then their logs/status read back.

**Step 1 — get the authorization URL.** Run the **Spotify Auth URL** workflow
(`.github/workflows/spotify-auth-url.yml`). It runs `spotify_api/get_auth_url.py`
and prints the authorization URL in the logs. Send that URL to the user to open
in a browser and approve.

**Step 2 — exchange the code and update the secret.** After the user approves,
their browser is redirected to `http://127.0.0.1:8888/callback?code=...` (the
page fails to load — that is expected; the useful part is the URL in the address
bar). The user pastes that full URL back. Run the **Spotify Update Refresh
Token** workflow (`.github/workflows/spotify-update-token.yml`) with that URL as
the `redirect_url` input. It runs `spotify_api/update_refresh_token.py`, which
exchanges the code for a new refresh token and writes it to the `REFRESH_TOKEN`
secret via the GitHub REST API (encrypted with the repo's Actions public key
using pynacl's sealed box).

**Step 3 — verify.** Re-run the **Daily Spotify Shuffle** workflow
(`workflow_dispatch`) and confirm it succeeds.

### Why `GH_PAT` is needed

A workflow cannot write repository secrets using the built-in `GITHUB_TOKEN`.
The update workflow uses a `GH_PAT` secret instead: a Personal Access Token
allowed to write Actions secrets (a fine-grained PAT with the "Secrets"
repository permission set to Read and write, scoped to this repo, or a classic
PAT with the `repo` scope). If `GH_PAT` is missing or expired, the update
workflow succeeds at exchanging the code but fails at the secret-write step —
regenerate the PAT and update the `GH_PAT` secret.

### Gotchas

- The authorization code in the redirect URL is single-use and short-lived. If
  Step 2 fails after the exchange, the user must re-authenticate (Step 1 again).
- The redirect URL passed as a workflow input is recorded in that run's input
  history; it is a spent code, so this is harmless.
- Never print or commit the refresh token. `.env` is gitignored — keep it that
  way.
