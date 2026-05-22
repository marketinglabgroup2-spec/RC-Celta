#!/usr/bin/env python3
# Removes old event tag and adds new one for all subscribers in the audience.
import os, json, hashlib, urllib.request, base64
from urllib.error import HTTPError

DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env = {}
    with open(os.path.join(DIRECTORY, '.env')) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip()
    return env

ENV         = load_env()
MC_API_KEY  = ENV.get('MAILCHIMP_API_KEY', '')
MC_AUDIENCE = ENV.get('MAILCHIMP_AUDIENCE_ID', '')
MC_DC       = ENV.get('MAILCHIMP_DC', 'us1')
MC_BASE     = f'https://{MC_DC}.api.mailchimp.com/3.0'

OLD_EVENT_TAG = 'event:240895'
NEW_EVENT_TAG = 'event:4587'

def mc(method, path, payload=None):
    creds = base64.b64encode(f'anystring:{MC_API_KEY}'.encode()).decode()
    req = urllib.request.Request(
        f'{MC_BASE}{path}',
        data=json.dumps(payload).encode() if payload else None,
        headers={'Authorization': f'Basic {creds}', 'Content-Type': 'application/json'},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {}

# Get all subscribed members
status, body = mc('GET', f'/lists/{MC_AUDIENCE}/members?count=100&status=subscribed')
members = body.get('members', [])

for m in members:
    email = m['email_address']
    tag_names = [t['name'] for t in (m.get('tags') or [])]

    if OLD_EVENT_TAG not in tag_names:
        print(f'  skip  {email} — does not have {OLD_EVENT_TAG}')
        continue

    subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
    status, _ = mc('POST',
        f'/lists/{MC_AUDIENCE}/members/{subscriber_hash}/tags',
        {'tags': [
            {'name': OLD_EVENT_TAG, 'status': 'inactive'},
            {'name': NEW_EVENT_TAG, 'status': 'active'},
        ]}
    )
    print(f'  {"✓" if status == 204 else "✗"}  {email} — removed {OLD_EVENT_TAG}, added {NEW_EVENT_TAG}')
