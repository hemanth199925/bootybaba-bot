import os
import base64
import requests
import tempfile
import subprocess

GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY")
SIGHTENGINE_USER  = os.environ.get("SIGHTENGINE_USER")
SIGHTENGINE_SECRET= os.environ.get("SIGHTENGINE_SECRET")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


# ── Public entry point ────────────────────────────────────────────────────────

def analyze_image(file_path: str, source_label: str = "image") -> str:
    """
    Runs Sightengine + Gemini on a file (image or video).
    For videos, extracts a few frames first.
    Returns a single formatted reply string.
    """
    frames = extract_frames(file_path) if file_path.endswith(".mp4") else [file_path]

    se_score  = sightengine_check(frames[0])   # classifier score (0-1, higher = AI)
    gem_result = gemini_check(frames[0])        # {"verdict": str, "reason": str}

    return build_reply(se_score, gem_result, source_label, is_video=file_path.endswith(".mp4"))


# ── Frame extraction ──────────────────────────────────────────────────────────

def extract_frames(video_path: str):
    """Extract up to 4 evenly-spaced frames from a video using ffmpeg."""
    out_dir = tempfile.mkdtemp()
    out_pattern = os.path.join(out_dir, "frame_%02d.jpg")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "fps=1/2",          # one frame every 2 seconds
        "-frames:v", "4",
        "-q:v", "2",
        out_pattern, "-y"
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
    except Exception as e:
        print(f"[extract_frames] ffmpeg error: {e}")

    frames = sorted([
        os.path.join(out_dir, f)
        for f in os.listdir(out_dir)
        if f.endswith(".jpg")
    ])
    return frames if frames else [video_path]


# ── Sightengine ───────────────────────────────────────────────────────────────

def sightengine_check(image_path: str) -> float | None:
    """Returns AI probability 0-1, or None on error."""
    try:
        with open(image_path, "rb") as f:
            files = {"media": f}
            params = {
                "models": "genai",
                "api_user": SIGHTENGINE_USER,
                "api_secret": SIGHTENGINE_SECRET,
            }
            r = requests.post(
                "https://api.sightengine.com/1.0/check.json",
                files=files, data=params, timeout=20
            )
            r.raise_for_status()
            data = r.json()
            # genai.score is the AI-generated probability
            return data.get("type", {}).get("ai_generated")
    except Exception as e:
        print(f"[sightengine_check] error: {e}")
        return None


# ── Gemini ────────────────────────────────────────────────────────────────────

def gemini_check(image_path: str) -> dict:
    """Returns {"verdict": "AI"|"Real"|"Uncertain", "reason": str}"""
    try:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        prompt = (
            "You are an expert AI image forensics analyst. "
            "Analyze this image and tell me: is it AI-generated or a real photograph?\n\n"
            "Look for: unnatural skin/texture, distorted hands or fingers, "
            "inconsistent lighting, background anomalies, synthetic smoothness, "
            "text artifacts, or photographic grain/noise.\n\n"
            "Reply in this EXACT format (nothing else):\n"
            "VERDICT: AI | Real | Uncertain\n"
            "REASON: one short sentence explaining the main clue"
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                ]
            }]
        }

        r = requests.post(
            GEMINI_URL,
            json=payload,
            params={"key": GEMINI_API_KEY},
            timeout=30
        )
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

        verdict = "Uncertain"
        reason  = "Could not determine."

        for line in text.splitlines():
            if line.startswith("VERDICT:"):
                v = line.replace("VERDICT:", "").strip()
                if "AI" in v.upper():
                    verdict = "AI"
                elif "REAL" in v.upper():
                    verdict = "Real"
                else:
                    verdict = "Uncertain"
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

        return {"verdict": verdict, "reason": reason}

    except Exception as e:
        print(f"[gemini_check] error: {e}")
        return {"verdict": "Uncertain", "reason": "Analysis failed."}


# ── Build reply ───────────────────────────────────────────────────────────────

def build_reply(se_score, gem_result, source_label, is_video=False) -> str:
    gem_verdict = gem_result["verdict"]
    gem_reason  = gem_result["reason"]

    # Sightengine label
    if se_score is None:
        se_label = "⚠️ Unavailable"
        se_pct   = ""
    else:
        pct = round(se_score * 100)
        se_pct = f"{pct}%"
        if pct >= 60:
            se_label = f"🤖 AI-Generated ({pct}%)"
        elif pct <= 40:
            se_label = f"✅ Looks Real ({100 - pct}% real)"
        else:
            se_label = f"🤔 Uncertain ({pct}%)"

    # Gemini label
    gem_emoji = {"AI": "🤖", "Real": "✅", "Uncertain": "🤔"}.get(gem_verdict, "🤔")
    gem_label = f"{gem_emoji} {gem_verdict}"

    # Overall verdict — majority vote
    votes_ai   = sum([
        1 if (se_score or 0) >= 0.6 else 0,
        1 if gem_verdict == "AI" else 0
    ])
    votes_real = sum([
        1 if (se_score or 1) <= 0.4 else 0,
        1 if gem_verdict == "Real" else 0
    ])

    if votes_ai >= 2:
        overall = "🤖 AI-Generated"
    elif votes_real >= 2:
        overall = "✅ Looks Real"
    else:
        overall = "🤔 Not Sure"

    media_type = "video (sampled frames)" if is_video else source_label

    reply = (
        f"🔍 The Booty Baba has spoken...\n\n"
        f"{overall}\n\n"
        f"Sightengine → {se_label}\n"
        f"Gemini      → {gem_label}\n"
        f"             {gem_reason}\n\n"
        f"📎 ({media_type})\n"
        f"⚠️ No detector is 100% accurate."
    )
    return reply
