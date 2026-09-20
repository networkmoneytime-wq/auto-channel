"""One-time local script: run this yourself to mint a TikTok refresh token.

Requires TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET already set in .env (from
the TikTok developer app's credentials — see README). These identify the app,
not the posting account, so they're shared across every channel — the same
app can hold separate OAuth grants for as many TikTok accounts as you like.
The redirect URI below must exactly match what's configured in the app's
Login Kit settings.

    python scripts/setup_tiktok_oauth.py [--channel cars]

Opens a browser for you to log into the TikTok account you want this channel
to post as (while the app is unaudited/Sandbox, that account must be added
as a Target User in the app's Sandbox settings and set to Private), then
prints a refresh token to paste into .env / GitHub Actions secrets as
TIKTOK_REFRESH_TOKEN (or TIKTOK_REFRESH_TOKEN_<CHANNEL> with --channel).
"""

import hashlib
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from src.config import env  # noqa: E402

channel_suffix = ""
if len(sys.argv) == 3 and sys.argv[1] == "--channel":
    channel_suffix = "_" + sys.argv[2].upper()
elif len(sys.argv) != 1:
    print(__doc__)
    sys.exit(1)

REDIRECT_URI = "http://localhost:8921/callback"
SCOPES = "user.info.basic,video.publish,video.upload"

auth_code = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        auth_code["code"] = params.get("code", [None])[0]
        auth_code["state"] = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Done, you can close this tab.</body></html>")

    def log_message(self, *args):
        pass


def main() -> None:
    client_key = env("TIKTOK_CLIENT_KEY")
    client_secret = env("TIKTOK_CLIENT_SECRET")
    state = secrets.token_urlsafe(16)

    code_verifier = secrets.token_urlsafe(64)[:128]
    # TikTok's PKCE implementation deviates from RFC 7636: it wants the code
    # challenge as a hex digest of SHA256, not base64url.
    code_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()

    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(
        {
            "client_key": client_key,
            "response_type": "code",
            "scope": SCOPES,
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    print(f"Opening browser to authorize...\nIf it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8921), CallbackHandler)
    server.handle_request()  # blocks until the callback hits

    if auth_code.get("state") != state:
        print("State mismatch — aborting for safety.")
        sys.exit(1)
    code = auth_code.get("code")
    if not code:
        print("No authorization code received.")
        sys.exit(1)

    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "refresh_token" not in data:
        print("\nUnexpected response from TikTok:")
        print(data)
        sys.exit(1)
    print(f"\nTIKTOK_REFRESH_TOKEN{channel_suffix}=" + data["refresh_token"])


if __name__ == "__main__":
    main()
