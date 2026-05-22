#!/usr/bin/env python3
import os, sys, warnings
warnings.filterwarnings("ignore")
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL      = os.getenv("ONEBOX_BASE_URL", "").rstrip("/")
CHANNEL_ID    = os.getenv("ONEBOX_CHANNEL_ID")
CLIENT_ID     = os.getenv("ONEBOX_CLIENT_ID")
CLIENT_SECRET = os.getenv("ONEBOX_CLIENT_SECRET")

# 1. Authenticate
auth = requests.post(
    f"{BASE_URL}/oauth/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={"grant_type": "client_credentials", "channel_id": CHANNEL_ID,
          "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    timeout=15,
)
auth.raise_for_status()
token = auth.json()["access_token"]

# 2. Fetch all sessions (paginate until exhausted)
sessions, offset = [], 0
while True:
    resp = requests.get(
        f"{BASE_URL}/catalog-api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100, "offset": offset},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    page = body.get("data", [])
    sessions.extend(page)
    total = body.get("metadata", {}).get("total", len(sessions))
    if len(sessions) >= total or not page:
        break
    offset += len(page)

# 3. Report
print(f"\nTotal matches returned: {len(sessions)}")
if sessions:
    first = sessions[0]
    name  = first.get("name") or first.get("event", {}).get("name", "—")
    date  = first.get("date", {}).get("start", "—")
    venue = first.get("venue", {}).get("name", "—")
    print(f"\nFirst match:")
    print(f"  Name  : {name}")
    print(f"  Date  : {date}")
    print(f"  Venue : {venue}")
    print(f"  ID    : {first.get('id')}")
print()
