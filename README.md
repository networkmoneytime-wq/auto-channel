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
   add the "Content Posting API" product.
2. **Important:** unaudited apps can only post as `SELF_ONLY` (private drafts
   visible to you only). Public posting needs TikTok's app audit, which can
   take days to weeks. Start in `SELF_ONLY` (already the default in
   `config/config.yaml`) and switch to `PUBLIC_TO_EVERYONE` once approved.
3. Complete the OAuth flow for your own creator account (TikTok's docs walk
   through the redirect URI + code exchange) to get a refresh token.
4. Fill in `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`.

## 5. Instagram Graph API

1. Your Instagram account must be a **Business or Creator account**, linked
   to a Facebook Page.
2. developers.facebook.com → create an app → add "Instagram Graph API".
3. Generate a long-lived access token for that Page/IG account with the
   `instagram_content_publish` permission (Graph API Explorer works for
   testing; for production use a proper token exchange).
4. Get your IG user ID (Graph API Explorer: `GET /me/accounts`, then the
   linked `instagram_business_account` id).
5. Fill in `IG_ACCESS_TOKEN`, `IG_USER_ID`. Note: long-lived tokens expire
   (~60 days) and need refreshing — not automated here yet.

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
