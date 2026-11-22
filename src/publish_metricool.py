import json, os, sys
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import requests
token=os.getenv("METRICOOL_API_TOKEN","").strip()
if not token:
    print("METRICOOL_API_TOKEN missing: video generated; Metricool publish skipped.")
    sys.exit(0)
video=os.getenv("VIDEO_URL","")
if not video.startswith("https://"): raise SystemExit("Missing public VIDEO_URL")
with open("metadata.json",encoding="utf-8") as f: meta=json.load(f)
tz=os.getenv("METRICOOL_TIMEZONE","Asia/Baghdad")
now=datetime.now(ZoneInfo(tz)); publish=(now+timedelta(minutes=10)).replace(second=0,microsecond=0)
body={"publicationDate":{"dateTime":publish.strftime("%Y-%m-%dT%H:%M:%S"),"timezone":tz},
"text":meta["description"],"providers":[{"network":"youtube"},{"network":"tiktok"}],
"media":[video],"saveExternalMediaFiles":True,"autoPublish":True,"draft":False,
"youtubeData":{"type":"short","title":meta["title"],"privacy":"public","madeForKids":False,"isAiGeneratedContent":False},
"tiktokData":{"title":meta["title"],"privacyOption":"PUBLIC_TO_EVERYONE","isAigc":False}}
url=f'https://app.metricool.com/api/v2/scheduler/posts?blogId={os.getenv("METRICOOL_BLOG_ID","8234676")}&userId={os.getenv("METRICOOL_USER_ID","6485386")}'
r=requests.post(url,headers={"X-Mc-Auth":token,"Content-Type":"application/json","Accept":"application/json"},json=body,timeout=240)
if not r.ok: raise SystemExit(f"Metricool API error {r.status_code}: {r.text[:1000]}")
print("Metricool scheduled:",r.text[:2000]); print("Publish time:",publish.isoformat())
