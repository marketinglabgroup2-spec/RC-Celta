#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
import urllib.request
import urllib.parse
import base64
import hashlib
from urllib.error import HTTPError

PORT = 8080
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


def _mc_request(method, path, payload=None):
    credentials = base64.b64encode(f'anystring:{MC_API_KEY}'.encode()).decode()
    req = urllib.request.Request(
        f'{MC_BASE}{path}',
        data=json.dumps(payload).encode('utf-8') if payload is not None else None,
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type':  'application/json',
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {}


def subscribe(nombre, apellidos, email, event_id, event_name, grada_id, grada_name):
    # 1. Upsert member (subscribed status, all merge fields)
    subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()

    status, body = _mc_request('PUT',
        f'/lists/{MC_AUDIENCE}/members/{subscriber_hash}',
        {
            'email_address': email,
            'status_if_new': 'subscribed',
            'merge_fields': {
                'FNAME':      nombre,
                'LNAME':      apellidos,
                'EVENT_ID':   str(event_id),
                'EVENT_NAME': event_name,
                'GRADA_ID':   str(grada_id),
                'GRADA_NAME': grada_name,
                'GDPR':       'yes',
            },
        }
    )

    if status not in (200, 201):
        detail = body.get('detail') or body.get('title') or 'Mailchimp error'
        return False, detail

    # 2. Apply segmentation tags
    tags = [
        {'name': f'event:{event_id}',  'status': 'active'},
        {'name': f'grada:{grada_id}',  'status': 'active'},
        {'name': 'source:avisame',     'status': 'active'},
    ]
    _mc_request('POST',
        f'/lists/{MC_AUDIENCE}/members/{subscriber_hash}/tags',
        {'tags': tags}
    )

    return True, body.get('status', 'subscribed')


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} — {fmt % args}')

    def do_POST(self):
        if self.path != '/subscribe':
            self.send_error(404)
            return

        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        ct     = self.headers.get('Content-Type', '')
        data   = json.loads(raw) if 'application/json' in ct \
                 else dict(urllib.parse.parse_qsl(raw.decode('utf-8')))

        nombre     = data.get('nombre',     '').strip()
        apellidos  = data.get('apellidos',  '').strip()
        email      = data.get('email',      '').strip()
        event_id   = data.get('event_id',   '').strip()
        event_name = data.get('event_name', '').strip()
        grada_id   = data.get('grada_id',   '').strip()
        grada_name = data.get('grada_name', '').strip()

        if not all([nombre, apellidos, email, grada_id]):
            self._json(400, {'ok': False, 'error': 'Faltan campos obligatorios.'})
            return

        ok, result = subscribe(nombre, apellidos, email,
                               event_id, event_name, grada_id, grada_name)

        if ok:
            print(f'  ✓  {email} | event:{event_id} | grada:{grada_id} | tags applied')
            self._json(200, {'ok': True, 'message': '¡Te avisaremos en cuanto salgan las entradas!'})
        else:
            print(f'  ✗  {email} — {result}')
            self._json(500, {'ok': False, 'error': result})

    def _json(self, code, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',  'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


print(f'Serving RC Celta ¡Avísame! at http://localhost:{PORT}/landing.html')
print('Press Ctrl+C to stop.\n')

with socketserver.TCPServer(('', PORT), Handler) as httpd:
    httpd.allow_reuse_address = True
    httpd.serve_forever()
