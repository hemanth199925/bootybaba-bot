import os
import requests
import tempfile
import subprocess
from flask import Flask, request, jsonify
from analyzer import analyze_image
from downloader import download_instagram_media

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "bootybaba_secret")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

# ── Webhook verification (Meta calls this once on setup) ──────────────────────
@app.route("/webhook", methods=["GET"])
def verify():
    mode  = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

# ── Receive DMs ───────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return "ok", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message   = event.get("message", {})
            if not sender_id or not message:
                continue

            # Ignore echoes
            if message.get("is_echo"):
                continue

            image_path = None
            source_label = ""

            # ── Case 1: Direct image attachment ──────────────────────────────
            attachments = message.get("attachments", [])
            for att in attachments:
                if att.get("type") in ("image", "video"):
                    media_url = att["payload"].get("url")
                    ext = ".mp4" if att["type"] == "video" else ".jpg"
                    image_path = download_direct(media_url, ext)
                    source_label = att["type"]
                    break

            # ── Case 2: Instagram link in text ────────────────────────────────
            if not image_path:
                text = message.get("text", "")
                if "instagram.com" in text:
                    url = text.strip().split()[0]
                    send_dm(sender_id, "🔍 Hang on, The Booty Baba is fetching that post...")
                    image_path = download_instagram_media(url)
                    source_label = "instagram link"

            if not image_path:
                send_dm(sender_id,
                    "👋 Send me an image, video (< 10s), or an Instagram post/reel link!")
                continue

            # ── Analyze ───────────────────────────────────────────────────────
            send_dm(sender_id, "🔍 The Booty Baba is analyzing...")
            verdict = analyze_image(image_path, source_label)
            send_dm(sender_id, verdict)

            # Cleanup
            try:
                os.remove(image_path)
            except Exception:
                pass

    return "ok", 200


def download_direct(url, ext=".jpg"):
    """Download a media file from a direct URL."""
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in r.iter_content(8192):
            tmp.write(chunk)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"[download_direct] error: {e}")
        return None


def send_dm(recipient_id, text):
    """Send a DM reply via Instagram Graph API."""
    url = f"https://graph.instagram.com/v19.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    params  = {"access_token": PAGE_ACCESS_TOKEN}
    try:
        r = requests.post(url, json=payload, headers=headers, params=params, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[send_dm] error: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
