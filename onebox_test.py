#!/usr/bin/env python3
"""
ONEBOX API tester
Checks credentials, lists sessions, and fetches availability for the first session.
"""
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")  # suppress LibreSSL urllib3 noise on macOS

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL       = os.getenv("ONEBOX_BASE_URL", "").rstrip("/")
CHANNEL_ID     = os.getenv("ONEBOX_CHANNEL_ID", "")
CLIENT_ID      = os.getenv("ONEBOX_CLIENT_ID", "")
CLIENT_SECRET  = os.getenv("ONEBOX_CLIENT_SECRET", "")

BOLD  = "\033[1m"
GREEN = "\033[32m"
RED   = "\033[31m"
CYAN  = "\033[36m"
RESET = "\033[0m"


def pretty(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def check(label: str, ok: bool, detail: str = "") -> None:
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    print(f"  {icon}  {label}" + (f"  —  {detail}" if detail else ""))


def step(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─'*55}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*55}{RESET}")


# ── 0. Env sanity check ────────────────────────────────────────
step("0 / Environment")
check("ONEBOX_BASE_URL",      bool(BASE_URL),      BASE_URL or "MISSING")
check("ONEBOX_CHANNEL_ID",    bool(CHANNEL_ID),    CHANNEL_ID or "MISSING")
check("ONEBOX_CLIENT_ID",     bool(CLIENT_ID),     CLIENT_ID or "MISSING")
check("ONEBOX_CLIENT_SECRET", bool(CLIENT_SECRET), "***" if CLIENT_SECRET else "MISSING")

if not all([BASE_URL, CHANNEL_ID, CLIENT_ID, CLIENT_SECRET]):
    print(f"\n{RED}  Fill in all values in .env and try again.{RESET}\n")
    sys.exit(1)


# ── 1. Authentication ──────────────────────────────────────────
step("1 / Authentication  —  POST /oauth/token")

auth_resp = requests.post(
    f"{BASE_URL}/oauth/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "grant_type":    "client_credentials",
        "channel_id":    CHANNEL_ID,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
    timeout=15,
)

print(f"\n  Status  : {auth_resp.status_code}")

if auth_resp.status_code == 200:
    auth_data = auth_resp.json()
    token = auth_data.get("access_token") or auth_data.get("token")
    check("Credentials valid", bool(token))
    check("Token received",    bool(token), f"{token[:24]}…" if token else "—")
    if "expires_in" in auth_data:
        check("Expires in", True, f"{auth_data['expires_in']}s")
    print(f"\n  Full response:\n{pretty(auth_data)}")
else:
    check("Credentials valid", False, f"HTTP {auth_resp.status_code}")
    try:
        print(f"\n  Error body:\n{pretty(auth_resp.json())}")
    except Exception:
        print(f"\n  Raw body: {auth_resp.text[:400]}")
    sys.exit(1)


# ── 2. Sessions ────────────────────────────────────────────────
step("2 / Sessions  —  GET /catalog-api/v1/sessions")

sessions_resp = requests.get(
    f"{BASE_URL}/catalog-api/v1/sessions",
    headers={"Authorization": f"Bearer {token}"},
    timeout=15,
)

print(f"\n  Status  : {sessions_resp.status_code}")

if sessions_resp.status_code == 200:
    sessions_data = sessions_resp.json()
    sessions = (
        sessions_data if isinstance(sessions_data, list)
        else sessions_data.get("data")
        or sessions_data.get("sessions")
        or sessions_data
    )
    count = len(sessions) if isinstance(sessions, list) else "?"
    check("Sessions endpoint reachable", True)
    check("Sessions returned", bool(count), f"{count} session(s)")
    print(f"\n  Full response:\n{pretty(sessions_data)}")
else:
    check("Sessions endpoint reachable", False, f"HTTP {sessions_resp.status_code}")
    try:
        print(f"\n  Error body:\n{pretty(sessions_resp.json())}")
    except Exception:
        print(f"\n  Raw body: {sessions_resp.text[:400]}")
    sys.exit(1)


# ── 3. Availability (first session) ───────────────────────────
step("3 / Availability  —  GET /catalog-api/v1/sessions/{sessionId}/availability")

sessions_list = sessions if isinstance(sessions, list) else []
first_session = sessions_list[0] if sessions_list else None
session_id = (
    first_session.get("id") or
    first_session.get("sessionId") or
    first_session.get("session_id")
) if first_session else None

if not session_id:
    print(f"\n  {RED}No session ID found to query availability.{RESET}")
    sys.exit(1)

print(f"\n  Using session ID: {session_id}")

avail_resp = requests.get(
    f"{BASE_URL}/catalog-api/v1/sessions/{session_id}/availability",
    headers={"Authorization": f"Bearer {token}"},
    timeout=15,
)

print(f"  Status  : {avail_resp.status_code}")

if avail_resp.status_code == 200:
    avail_data = avail_resp.json()
    sections = avail_data if isinstance(avail_data, list) else avail_data.get("sections", avail_data)
    count = len(sections) if isinstance(sections, list) else "?"
    check("Availability endpoint reachable", True)
    check("Sections returned", bool(count), f"{count} section(s)")
    print(f"\n  Full response:\n{pretty(avail_data)}")
else:
    check("Availability endpoint reachable", False, f"HTTP {avail_resp.status_code}")
    try:
        print(f"\n  Error body:\n{pretty(avail_resp.json())}")
    except Exception:
        print(f"\n  Raw body: {avail_resp.text[:400]}")

print(f"\n{GREEN}{BOLD}  Done.{RESET}\n")
