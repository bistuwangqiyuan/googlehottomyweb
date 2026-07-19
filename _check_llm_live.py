# -*- coding: utf-8 -*-
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
BASE = "https://trendflow-site.vercel.app"
ok = True
for slug in ("2026-07-19-football-score", "2026-07-19-super-bowl", "2026-07-19-otamendi"):
    r = requests.get(f"{BASE}/briefings/{slug}", timeout=20)
    good = r.status_code == 200 and 'data-testid="ai-disclosure"' in r.text
    ok = ok and good
    print(f"{slug}: status={r.status_code} ai-disclosure={'ai-disclosure' in r.text}")
print("ALL LIVE" if ok else "NOT YET")
