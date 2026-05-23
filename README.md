# 🔍 The Booty Baba — AI Image Detector Bot

Instagram DM bot that detects AI-generated images and videos using Gemini + Sightengine.

---

## Files
- `app.py` — Flask webhook server
- `analyzer.py` — Gemini + Sightengine analysis logic
- `downloader.py` — Instagram link downloader (instaloader)
- `requirements.txt` — Python dependencies
- `render.yaml` — Render.com deployment config

---

## Environment Variables (set in Render.com dashboard)

| Variable | Where to get it |
|---|---|
| `PAGE_ACCESS_TOKEN` | Meta Developer → App → Instagram → Access Token |
| `VERIFY_TOKEN` | Make up any secret string e.g. `bootybaba_secret` |
| `GEMINI_API_KEY` | aistudio.google.com → Get API Key |
| `SIGHTENGINE_USER` | sightengine.com → Dashboard → API Keys |
| `SIGHTENGINE_SECRET` | sightengine.com → Dashboard → API Keys |

---

## Deployment Steps

### Step 1 — Push to GitHub
1. Create a new GitHub repo (e.g. `bootybaba-bot`)
2. Upload all these files to it

### Step 2 — Deploy on Render.com
1. Go to render.com → New → Web Service
2. Connect your GitHub repo
3. Render auto-detects `render.yaml`
4. Go to Environment → add all variables above
5. Click Deploy
6. Copy your Render URL (e.g. `https://bootybaba-bot.onrender.com`)

### Step 3 — Connect Instagram Webhook
1. Go to developers.facebook.com → Your App
2. Add Product → Messenger (supports Instagram DMs)
3. Settings → Webhooks → Add callback URL:
   `https://bootybaba-bot.onrender.com/webhook`
4. Verify token: whatever you set as `VERIFY_TOKEN`
5. Subscribe to: `messages`
6. Connect your Instagram Business account

### Step 4 — Get Page Access Token
1. In Meta Developer → Tools → Graph API Explorer
2. Select your App and Instagram account
3. Generate token with `instagram_manage_messages` permission
4. Copy it → paste as `PAGE_ACCESS_TOKEN` in Render

### Step 5 — Test!
Send a DM to @madmanwritings_ with:
- An image
- A video under 10 seconds
- An Instagram post or reel link

---

## Example Replies

```
🔍 The Booty Baba has spoken...

🤖 AI-Generated

Sightengine → 🤖 AI-Generated (87%)
Gemini      → 🤖 AI
             Hands show unnatural finger structure.

📎 (image)
⚠️ No detector is 100% accurate.
```

```
🔍 The Booty Baba has spoken...

✅ Looks Real

Sightengine → ✅ Looks Real (91% real)
Gemini      → ✅ Real
             Natural grain and consistent lighting detected.

📎 (instagram link)
⚠️ No detector is 100% accurate.
```
