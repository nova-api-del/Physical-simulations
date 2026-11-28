"""Upload output.mp4 to YouTube using the official Data API (OAuth refresh token).

Secrets come from the environment and are never printed. If they are not set,
the script skips publishing and exits successfully.
"""
import json, os, sys
from pathlib import Path
import requests

NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def fail(stage, response):
    try:
        error = response.json().get("error")
        if isinstance(error, dict):
            reasons = [e.get("reason") for e in error.get("errors", [])]
            error = f"{error.get('message')} {reasons}"
    except ValueError:
        error = "no JSON body"
    raise SystemExit(f"YouTube {stage} failed: HTTP {response.status_code}: {error}")


def main():
    creds = {n: os.getenv(n, "").strip() for n in NAMES}
    missing = [n for n, v in creds.items() if not v]
    if missing:
        print("Publishing skipped. Missing secrets: " + ", ".join(missing))
        return
    video = Path("output.mp4")
    meta = json.loads(Path("metadata.json").read_text(encoding="utf-8"))

    r = requests.post(TOKEN_URL, timeout=60, data={
        "client_id": creds["YOUTUBE_CLIENT_ID"],
        "client_secret": creds["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": creds["YOUTUBE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"})
    if not r.ok:
        fail("login", r)
    auth = {"Authorization": "Bearer " + r.json()["access_token"]}

    privacy = os.getenv("YOUTUBE_PRIVACY", "").strip() or "public"
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"],
                    "tags": meta["tags"], "categoryId": "24"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    r = requests.post(UPLOAD_URL, timeout=60,
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={**auth, "X-Upload-Content-Type": "video/mp4",
                               "X-Upload-Content-Length": str(video.stat().st_size)},
                      json=body)
    if not r.ok:
        fail("upload start", r)
    # One attempt only: blindly retrying an upload can create duplicate videos.
    with video.open("rb") as f:
        r = requests.put(r.headers["Location"], data=f, timeout=900,
                         headers={**auth, "Content-Type": "video/mp4"})
    if not r.ok:
        fail("upload", r)
    result = r.json()
    status = result.get("status", {}).get("privacyStatus")
    print(f"Published: https://youtube.com/shorts/{result['id']} (privacy: {status})")


if __name__ == "__main__":
    sys.exit(main())
