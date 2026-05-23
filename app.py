import os
import requests
import tempfile
from flask import Flask, request, jsonify
from analyzer import analyze_image
from downloader import download_instagram_media

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return "The Booty Baba is alive!", 200


# ── Telegram Webhook ──────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return "ok", 200

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return "ok", 200

    image_path = None
    source_label = ""

    # ── Case 1: Photo sent directly ───────────────────────────────────────────
    if "photo" in message:
        # Telegram sends multiple sizes — pick the largest
        photo = message["photo"][-1]
        file_id = photo["file_id"]
        image_path = download_telegram_file(file_id, ".jpg")
        source_label = "image"

    # ── Case 2: Video sent directly ───────────────────────────────────────────
    elif "video" in message:
        video = message["video"]
        duration = video.get("duration", 999)
        if duration > 10:
            send_message(chat_id,
                "⏱ The Booty Baba only accepts videos under 10 seconds!\nTrim it and send again.")
            return "ok", 200
        file_id = video["file_id"]
        image_path = download_telegram_file(file_id, ".mp4")
        source_label = "video"

    # ── Case 3: Instagram link in text ────────────────────────────────────────
    elif "text" in message:
        text = message["text"].strip()
        if "instagram.com" in text:
            send_message(chat_id, "🔍 Hang on, The Booty Baba is fetching that post...")
            image_path = download_instagram_media(text.split()[0])
            source_label = "instagram link"
            if not image_path:
                send_message(chat_id,
                    "🔒 Couldn't fetch that post.\n"
                    "It might be private — send me the image/video directly instead!")
                return "ok", 200
        else:
            send_message(chat_id,
                "👋 Send me an image, video (< 10s), or an Instagram post/reel link!\n"
                "I'll tell you if it's AI-generated or real.")
            return "ok", 200

    # ── Document (file sent as file not compressed) ───────────────────────────
    elif "document" in message:
        doc = message["document"]
        mime = doc.get("mime_type", "")
        if mime.startswith("image/"):
            image_path = download_telegram_file(doc["file_id"], ".jpg")
            source_label = "image"
        elif mime.startswith("video/"):
            image_path = download_telegram_file(doc["file_id"], ".mp4")
            source_label = "video"

    if not image_path:
        send_message(chat_id,
            "👋 Send me an image, video (< 10s), or an Instagram post/reel link!")
        return "ok", 200

    # ── Analyze ───────────────────────────────────────────────────────────────
    send_message(chat_id, "🔍 The Booty Baba is analyzing...")
    verdict = analyze_image(image_path, source_label)
    send_message(chat_id, verdict)

    # Cleanup
    try:
        os.remove(image_path)
    except Exception:
        pass

    return "ok", 200


# ── Helpers ───────────────────────────────────────────────────────────────────

def download_telegram_file(file_id, ext=".jpg"):
    """Download a file from Telegram servers."""
    try:
        # Get file path
        r = requests.get(f"{TELEGRAM_API}/getFile",
                         params={"file_id": file_id}, timeout=10)
        r.raise_for_status()
        file_path = r.json()["result"]["file_path"]

        # Download file
        url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        r2 = requests.get(url, timeout=30, stream=True)
        r2.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in r2.iter_content(8192):
            tmp.write(chunk)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"[download_telegram_file] error: {e}")
        return None


def send_message(chat_id, text):
    """Send a Telegram message."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except Exception as e:
        print(f"[send_message] error: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
