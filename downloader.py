import os
import re
import tempfile
import instaloader

_loader = None

def _get_loader():
    global _loader
    if _loader is None:
        _loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            post_metadata_txt_pattern="",
            quiet=True,
        )
        # No login — works for all public posts/reels
        # Private posts will be handled gracefully with a friendly message
    return _loader


def _shortcode_from_url(url: str) -> str | None:
    """Extract shortcode from instagram.com/p/CODE or /reel/CODE."""
    match = re.search(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def download_instagram_media(url: str) -> str | None:
    """
    Download the first image or video from an Instagram post/reel URL.
    Returns the local file path, or None on failure.
    """
    shortcode = _shortcode_from_url(url)
    if not shortcode:
        print(f"[downloader] could not extract shortcode from: {url}")
        return None

    tmp_dir = tempfile.mkdtemp()
    try:
        loader = _get_loader()
        post   = instaloader.Post.from_shortcode(loader.context, shortcode)

        # Download into tmp_dir
        loader.dirname_pattern = tmp_dir
        loader.download_post(post, target=tmp_dir)

        # Find the downloaded media file
        for fname in os.listdir(tmp_dir):
            if fname.endswith((".jpg", ".jpeg", ".png", ".mp4")):
                return os.path.join(tmp_dir, fname)

        print("[downloader] no media file found after download")
        return None

    except instaloader.exceptions.PrivateProfileNotFollowedException:
        print("[downloader] private post — cannot access")
        return None
    except Exception as e:
        print(f"[downloader] error: {e}")
        return None
