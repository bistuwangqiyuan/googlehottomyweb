# -*- coding: utf-8 -*-
import json
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
auth = json.load(open(r"C:\Users\Administrator\AppData\Roaming\xdg.data\com.vercel.cli\auth.json"))
token = auth["token"]
TEAM = "team_YGHwcSYBmIm8oX9Yq7bBoPWP"
H = {"Authorization": f"Bearer {token}"}

r = requests.get(
    f"https://api.vercel.com/v6/deployments?projectId=prj_eEWfUA84AEDuqMICHy0vZRaY6ZAR&teamId={TEAM}&limit=8",
    headers=H, timeout=30)
r.raise_for_status()
for d in r.json()["deployments"]:
    meta = d.get("meta", {})
    print(f"{d['uid'][:28]} state={d.get('state'):<10} readyState={d.get('readyState', '?'):<10} "
          f"created={d['created']} source={d.get('source', '?'):<12} "
          f"commit={meta.get('githubCommitMessage', '')[:48]!r} author={meta.get('githubCommitAuthorName', '')}")
    if d.get("state") in ("QUEUED", "BUILDING", "INITIALIZING"):
        r2 = requests.get(f"https://api.vercel.com/v13/deployments/{d['uid']}?teamId={TEAM}",
                          headers=H, timeout=30)
        j = r2.json()
        print("   detail:", {k: j.get(k) for k in ("readyState", "readySubstate", "errorMessage", "errorCode")})
