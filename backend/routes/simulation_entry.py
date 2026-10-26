"""GoPhish click gateway: verify campaign telemetry before choosing exam or landing page."""
import hmac
import os
import re
from urllib.parse import urlsplit, urlunsplit
import requests
from flask import Blueprint, Response, jsonify, redirect, request
import database
import gophish_client
from security import authenticate_session_request
from services.campaign_materials import education_url

simulation_entry_bp = Blueprint('simulation_entry', __name__)


def entry_url():
    explicit = os.environ.get('SIMULATION_ENTRY_URL', '').strip()
    base = os.environ.get('SERVER_BASE_URL', '').rstrip('/')
    value = explicit or (base + '/simulation/entry' if base else '')
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
        raise ValueError('Configure SERVER_BASE_URL or SIMULATION_ENTRY_URL for campaign assessments.')
    return value


@simulation_entry_bp.route('/simulation/entry', methods=['GET', 'POST'])
def enter():
    rid = request.args.get('rid', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,128}', rid):
        return jsonify({'error': 'Invalid simulation link.'}), 400
    # The employee cannot choose an upstream host or path. Never forward credentials.
    upstream = os.environ.get('GOPHISH_PHISH_INTERNAL_URL', 'http://gophish:80').rstrip('/')
    parsed = urlsplit(upstream)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        return jsonify({'error': 'Simulation service is not configured.'}), 503
    try:
        response = requests.request(request.method, upstream + '/', params={'rid': rid},
            **({'data': {}} if request.method == 'POST' else {}), timeout=(3, 8), allow_redirects=False)
        if request.method == 'GET' and response.status_code == 200:
            for campaign in gophish_client.get_campaigns():
                recipient = next((r for r in campaign.get('results', []) if hmac.compare_digest(str(r.get('id', '')), rid)), None)
                if not recipient:
                    continue
                database.sync_gophish_events(campaign)
                # A RID only identifies a campaign recipient; it never signs them in.
                from contextlib import closing
                with closing(database.get_connection()) as conn:
                    row = conn.execute('''SELECT e.id FROM learning_exams e JOIN employee_accounts a
                        ON a.id=e.account_id WHERE a.email=? COLLATE NOCASE AND e.status!='completed'
                        AND a.role='employee' AND a.is_active=1 LIMIT 1''', (recipient['email'],)).fetchone()
                if row:
                    identity = authenticate_session_request(request)
                    destination = urlsplit(education_url())
                    path = '/exam' if identity and identity.role == 'employee' and identity.email.lower() == recipient['email'].lower() else '/simulation/education'
                    return redirect(urlunsplit((destination.scheme, destination.netloc, path, '', '')))
                break
        elif request.method == 'POST' and response.status_code in (200, 301, 302, 303):
            # No password/email fields were sent upstream. GoPhish records submission only.
            return redirect(education_url(), code=303)
        result = Response(response.content, status=response.status_code, content_type=response.headers.get('Content-Type', 'text/html'))
        result.headers['Cache-Control'] = 'no-store'
        result.headers['Referrer-Policy'] = 'no-referrer'
        return result
    except (requests.RequestException, gophish_client.GoPhishError):
        return jsonify({'error': 'Simulation verification is unavailable. Please retry this link.'}), 503


@simulation_entry_bp.route('/simulation/entry/track', methods=['GET'])
def track():
    """Preserve GoPhish email-open tracking when a campaign uses the click gateway."""
    rid = request.args.get('rid', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,128}', rid):
        return '', 400
    upstream = os.environ.get('GOPHISH_PHISH_INTERNAL_URL', 'http://gophish:80').rstrip('/')
    try:
        response = requests.get(upstream + '/track', params={'rid': rid}, timeout=(3, 8), allow_redirects=False)
        return Response(response.content, status=response.status_code,
            content_type=response.headers.get('Content-Type', 'image/png'), headers={'Cache-Control': 'no-store'})
    except requests.RequestException:
        return '', 503
