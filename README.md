# auto-channel

Fully automated faceless short-form video channel: picks a topic, writes a
script with an LLM, generates voiceover + burned-in captions + stock B-roll,
assembles a vertical video with ffmpeg, writes platform metadata, and uploads
to YouTube Shorts, TikTok, and Instagram Reels. Runs on a daily schedule via
GitHub Actions, so it needs no server of your own.

Everything is built on free tiers: Groq (LLM), edge-tts (voice, unofficial
free API), Pexels (stock video). The platform upload APIs are free but each
needs its own developer app — that setup is the part only you can do, below.

## How it works

```
topics.txt --> script_gen (Groq LLM) --> voiceover (edge-tts) --> captions
                                       --> visuals (Pexels)   --> ffmpeg assemble
                                                                       |
                                                                       v
                                              youtube.py / tiktok.py / instagram.py
```

State (which topics have been used, upload history) lives in `state/state.json`
and is committed back to the repo by the GitHub Action after each run, since
Actions runners are thrown away between runs.

**Scope note:** this MVP produces one video format — vertical, under 60s —
posted as-is to all three platforms (YouTube Shorts, TikTok, Reels all accept
this format). Long-form YouTube needs a structurally different, longer script
and isn't wired up yet; see "Extending" below.

## 1. Local setup

```bash
brew install ffmpeg   # or your OS's package manager
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Get your free API keys

**Groq (LLM)** — console.groq.com → API Keys → create one → `GROQ_API_KEY`.
Free tier is generous for this volume (a few requests per video).

**Pexels (stock video)** — pexels.com/api → request access (instant, free) →
`PEXELS_API_KEY`.

**edge-tts** — no key needed. It's an unofficial wrapper around Microsoft
Edge's "Read Aloud" service, so treat it as best-effort: if it ever breaks,
swap in another TTS provider in `src/pipeline/voiceover.py`.

## 3. YouTube Data API

1. console.cloud.google.com → new project → enable "YouTube Data API v3".
2. OAuth consent screen → External → add yourself as a test user (fine for
   personal automation; you don't need Google's app review for this).
3. Credentials → Create OAuth client → type **Desktop app** → download the
   JSON.
4. Run once locally to mint a refresh token:
   ```bash
   python scripts/setup_youtube_oauth.py path/to/client_secret.json
   ```
5. Copy the printed `YOUTUBE_REFRESH_TOKEN`, plus the client ID/secret from
   the downloaded JSON, into `.env` (and later into GitHub Secrets).

## 4. TikTok Content Posting API

1. developers.tiktok.com → register a developer account → create an app →
   add "Login Kit" and "Content Posting API" (Content Posting requires Login
   Kit). Also requires a Terms of Service URL, Privacy Policy URL, and app
   icon — this repo's `docs/` folder has minimal pages you can publish via
   GitHub Pages (Settings → Pages → Deploy from branch → `/docs`) and point
   the app config at.
2. Use the **Sandbox** tab (not Production) to test without a full app
   review: it has its own Client key/secret, and a "Target Users" list under
   Sandbox settings — add the TikTok account you want this channel to post
   as. Unaudited/Sandbox apps can only post to accounts on that list; public
   posting to any account needs TikTok's app audit (days to weeks). This
   matches `SELF_ONLY` privacy, already the default in `config/config.yaml`.
3. Under the app's Login Kit product, set platform to **Desktop**, and add
   redirect URI `http://localhost:8921/callback` (must match exactly what's
   in `scripts/setup_tiktok_oauth.py`).
4. Copy the Sandbox `Client key`/`Client secret` into `.env` as
   `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET`.
5. Run once locally to mint a refresh token:
   ```bash
   python scripts/setup_tiktok_oauth.py
   ```
   This opens a browser for you to log in as the target account and approve
   access, then prints `TIKTOK_REFRESH_TOKEN` to paste into `.env`.
4. Fill in `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`.

## 5. Instagram Graph API

1. Your Instagram account must be a **Business account** (Settings → Account
   type and tools → Switch to professional account — this step is
   mobile-app only, not available on the Instagram website), linked to a
   Facebook Page (create one during that same flow if you don't have one).
2. developers.facebook.com → register as a developer → create an app → add
   the use case "Manage messaging & content on Instagram".
3. In the use case's "API setup with Facebook login" tab, click "Add required
   content permissions" — this registers `instagram_basic`,
   `instagram_content_publish`, `pages_read_engagement`,
   `business_management`, `pages_show_list` on the app. (There's also a
   separate "API setup with Instagram login" tab using a different
   Instagram App ID/secret and different scope names — ignore that one, this
   repo's `src/uploaders/instagram.py` is written for the classic Graph API
   via Facebook Login.)
4. Under "Facebook Login for Business" → Settings, add a **Valid OAuth
   Redirect URI**. This repo's `docs/callback.html` (published via GitHub
   Pages) works as a redirect target — it's a static page that reads the
   token out of the URL fragment client-side, which is never sent to any
   server, so you can use it without hosting a backend of your own.
5. Get your Facebook App ID from the app dashboard, then visit this URL
   (replace `YOUR_APP_ID` and the redirect URI with your own GitHub Pages
   URL) signed into the Facebook account that manages the Page:
   ```
   https://www.facebook.com/v21.0/dialog/oauth?client_id=YOUR_APP_ID&redirect_uri=https://yourusername.github.io/auto-channel/callback.html&scope=instagram_basic,instagram_content_publish,pages_read_engagement,business_management,pages_show_list&response_type=token
   ```
   Approve the prompts (Pages / Businesses / Instagram accounts you want it
   to access). The callback page will show a `long_lived_token=...` value in
   the URL — that's valid ~60 days already, no separate exchange step
   needed.
6. Fill in `IG_ACCESS_TOKEN` (the `long_lived_token` value, not the shorter
   `access_token` near the start). Get `IG_USER_ID` from the "Choose the
   Instagram accounts..." step during authorization (shown next to the
   account's @handle), or via `GET /{page-id}?fields=instagram_business_account`.
   Note: long-lived tokens expire (~60 days) and need refreshing — not
   automated here yet.

## 6. Try it locally

```bash
python -m src.orchestrator
```

Turn platforms off in `config/config.yaml` (`enabled: false`) to test the
generation pipeline without uploading anywhere yet — the assembled video
lands in `output/last_run.mp4` either way.

## 7. Deploy the daily automation

1. Push this repo to GitHub.
2. Repo Settings → Secrets and variables → Actions → add every variable from
   `.env` as a secret (same names).
3. Settings → Actions → General → Workflow permissions → "Read and write
   permissions" (needed so the workflow can commit `state/state.json` back).
4. The workflow in `.github/workflows/publish.yml` runs daily at 15:00 UTC.
   Trigger it manually first from the Actions tab ("Run workflow") to check
   everything works end to end.

## Customizing

- `config/topics.txt` — one topic per line; edit freely, this is your content
  strategy.
- `config/config.yaml` — voice, video resolution, per-platform privacy/enable
  toggles, LLM model.
- `src/pipeline/script_gen.py` — the prompt that shapes tone/style.

## Before you turn this fully public

- **Review a handful of generated videos manually** before flipping any
  platform to public posting — quality control matters for both viewers and
  platform trust signals.
- **Disclosure requirements:** YouTube requires creators to label realistic
  AI-generated/altered content via the "Altered content" toggle in upload
  settings; this pipeline doesn't set that automatically since it's a policy
  judgment call depending on your content. TikTok and Instagram have similar
  AI-content labeling requirements. Check current policy for your content
  type before going public.
- **Spam/quality policies:** all three platforms restrict monetization or
  reach for "mass-produced" or "repetitious" content. Keep quality high and
  volume reasonable (this is built for ~1/day, not dozens).
- **Rate limits:** YouTube's free API quota is 10,000 units/day (~6 uploads);
  Pexels and Groq free tiers are per-minute/day limited — fine at this
  volume, worth checking their current limits if you scale up.

## Extending

- **Long-form YouTube:** add a second script-gen prompt for 3-10 minute
  content and a separate assemble path (more/longer clips, chaptering).
- **Background music:** mix a royalty-free track into `assemble.py`'s audio
  graph (currently voiceover-only).
- **Token refresh automation:** Instagram's long-lived token needs periodic
  refreshing; add a scheduled job hitting the refresh endpoint before expiry.
