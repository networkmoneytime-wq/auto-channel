"""One-time local script: run this yourself to mint a YouTube refresh token.

Either pass a downloaded OAuth client JSON (Desktop app type, see README):

    python scripts/setup_youtube_oauth.py path/to/client_secret.json

Or, for an additional channel whose YOUTUBE_CLIENT_ID_<CHANNEL> /
YOUTUBE_CLIENT_SECRET_<CHANNEL> are already saved in .env, skip the JSON
download entirely:

    python scripts/setup_youtube_oauth.py --channel cars

Either way this opens a browser for you to sign in and grant upload access,
then prints a refresh token to paste into .env / GitHub Actions secrets as
YOUTUBE_REFRESH_TOKEN (or YOUTUBE_REFRESH_TOKEN_<CHANNEL>).
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--channel":
        channel = sys.argv[2].upper()
        client_config = {
            "installed": {
                "client_id": os.environ[f"YOUTUBE_CLIENT_ID_{channel}"],
                "client_secret": os.environ[f"YOUTUBE_CLIENT_SECRET_{channel}"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    elif len(sys.argv) == 2:
        flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    else:
        print(__doc__)
        sys.exit(1)

    creds = flow.run_local_server(port=0)
    print("\nYOUTUBE_REFRESH_TOKEN=" + creds.refresh_token)


if __name__ == "__main__":
    main()
