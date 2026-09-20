"""One-time local script: run this yourself to mint a YouTube refresh token.

You need a Google Cloud OAuth client of type "Desktop app" first (see README).
Download its client secret JSON and pass its path as the only argument:

    python scripts/setup_youtube_oauth.py path/to/client_secret.json

This opens a browser for you to sign in and grant upload access, then prints
a refresh token to paste into your .env / GitHub Actions secrets as
YOUTUBE_REFRESH_TOKEN.
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0)
    print("\nYOUTUBE_REFRESH_TOKEN=" + creds.refresh_token)


if __name__ == "__main__":
    main()
