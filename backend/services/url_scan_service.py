"""Durable VT URL submission/polling for explicit employee actions, never traffic."""
import hashlib
import json
import time
from contextlib import closing

import database
import integrations


def queue(url, analysis):
    scan_id = hashlib.sha256(url.encode()).hexdigest()
    analysis = {**analysis, 'scanId': scan_id, 'pending': True}
    analysis['providerStatus']['virustotal'] = {'state': 'queued', 'statusCode': 0}
    with closing(database.get_connection()) as conn, conn:
        conn.execute('''INSERT INTO url_analysis_jobs(id,url,analysis_json,expires_at)
            VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET analysis_json=excluded.analysis_json,
            analysis_id=NULL, done=0,attempts=0,available_at=0,lease_until=0,expires_at=excluded.expires_at
            WHERE url_analysis_jobs.done=1 AND url_analysis_jobs.lease_until=0''',
            (scan_id, url, json.dumps(analysis), int(time.time()) + 3600))
        row = conn.execute('SELECT analysis_json FROM url_analysis_jobs WHERE id=?', (scan_id,)).fetchone()
    return json.loads(row['analysis_json'])


def grant(identity, scan_id):
    if scan_id:
        with closing(database.get_connection()) as conn, conn:
            conn.execute('INSERT OR IGNORE INTO url_scan_access VALUES(?,?)', (identity.account_id, scan_id))


def result(identity, scan_id):
    with closing(database.get_connection()) as conn:
        row = conn.execute('''SELECT j.analysis_json FROM url_analysis_jobs j JOIN url_scan_access a
            ON a.scan_id=j.id WHERE a.account_id=? AND j.id=?''', (identity.account_id, scan_id)).fetchone()
    return json.loads(row['analysis_json']) if row else None


def process_one():
    now = int(time.time())
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT * FROM url_analysis_jobs WHERE done=0 AND available_at<=?
            AND lease_until<=? ORDER BY available_at,id LIMIT 1''', (now, now)).fetchone()
        if not row:
            return False
        conn.execute('UPDATE url_analysis_jobs SET lease_until=?,attempts=attempts+1 WHERE id=?', (now + 90, row['id']))
    analysis = json.loads(row['analysis_json'])
    analysis_id, done = row['analysis_id'], False
    if now >= row['expires_at'] or row['attempts'] >= 30:
        response = {'provider': 'virustotal', 'success': False, 'state': 'expired', 'status_code': 408}
        done = True
    elif analysis_id:
        response = integrations.poll_vt_analysis(analysis_id)
    else:
        # A 404 lookup alone never meant the link was scanned. Submit it once.
        response = integrations.vt_file_request('POST', 'urls', data={'url': row['url']})
        if response.get('success'):
            analysis_id = ((response.get('data') or {}).get('data') or {}).get('id')
            if not isinstance(analysis_id, str):
                response.update(success=False, status_code=502)
                analysis_id, done = None, True
        elif response.get('status_code') != 429:
            done = True  # An uncertain POST must not be silently submitted again.
    attributes = (((response.get('data') or {}).get('data') or {}).get('attributes') or {})
    item = integrations.normalize_virustotal(response)
    if item:
        analysis.setdefault('evidence', {})['virustotal'] = item
    analysis.setdefault('providerStatus', {})['virustotal'] = integrations.provider_status(response)
    if response.get('success') and attributes.get('status') == 'completed':
        done = True
    elif response.get('success') and analysis_id:
        analysis['providerStatus']['virustotal']['state'] = 'pending'
    if response.get('status_code') in (401, 403):
        done = True
    from services.report_service import summarize
    analysis = {**summarize(analysis.get('evidence', {}), analysis['providerStatus'], 4),
                'scanId': row['id'], 'pending': not done}
    with closing(database.get_connection()) as conn, conn:
        reports = conn.execute("SELECT email,verdict FROM employee_url_reports WHERE url=? AND report_type='url'", (row['url'],)).fetchall()
        if done and analysis['verdict'] in ('malicious', 'suspicious'):
            for report in reports:
                if report['verdict'] not in ('malicious', 'suspicious'):
                    database.award_threat_reward(report['email'], row['url'], analysis['verdict'], connection=conn)
                    database.create_threat_report(report['email'], None, 'url', row['url'], analysis['verdict'],
                        analysis['severity'], 'both', raw_scores=analysis, connection=conn)
        conn.execute('''UPDATE url_analysis_jobs SET analysis_json=?,analysis_id=?,done=?,lease_until=0,
            available_at=?,updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (json.dumps(analysis), analysis_id, int(done), now + 60, row['id']))
        conn.execute("UPDATE employee_url_reports SET verdict=?,analysis_json=? WHERE url=? AND report_type='url'",
                     (analysis['verdict'], json.dumps(analysis), row['url']))
        # Evidence refresh never changes a SOC policy or overwrites its resolution.
        conn.execute('''UPDATE incidents SET vt_verdict=?,urlscan_verdict=? WHERE reported_url=?
            AND employee_report_id IS NOT NULL AND status='open' ''',
            (analysis.get('evidence', {}).get('virustotal', {}).get('verdict'),
             analysis.get('evidence', {}).get('urlscan', {}).get('verdict'), row['url']))
    if done and analysis.get('evidence'):
        database.save_threat_cache(row['url'], 'url', analysis)
    if reports:
        from services.proxy_store import publish_alert
        publish_alert({'type': 'incident.evidence', 'scanId': row['id']})
    return True
