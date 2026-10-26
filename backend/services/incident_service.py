"""Owned SOC triage: take a report, then resolve with a reason and real policy."""
import json
from contextlib import closing

import database
from services import proxy_service, proxy_store


class IncidentConflict(ValueError):
    pass


def restore_historical_resolutions():
    """Import old SOC outcomes once; never reopen a previously resolved report."""
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        rows = conn.execute('SELECT * FROM incidents WHERE historical_import=1').fetchall()
        for row in rows:
            before = dict(row)
            prior = proxy_store.get_historical_report_resolution(row['proxy_alert_id']) if row['proxy_alert_id'] else None
            if prior and prior['status'] in ('blocked', 'allowed') and row['status'] == 'open' and not row['assigned_to']:
                action = 'block' if prior['status'] == 'blocked' else 'allow'
                reason = prior.get('reason') or 'Imported previously resolved SOC alert; original reason is unavailable.'
                actor = prior.get('actor_email') or prior.get('resolved_by') or 'system:migration'
                actor_role = prior.get('actor_role') or 'system'
                timestamp = str(prior.get('decision_at') or prior.get('resolved_at') or '') or None
                conn.execute('''UPDATE incidents SET status='closed',resolution=?,resolution_reason=?,resolved_by=?,
                    closed_at=COALESCE(?,CURRENT_TIMESTAMP) WHERE ticket_id=?''',
                    (action, reason, actor, timestamp, row['ticket_id']))
                after = dict(conn.execute('SELECT * FROM incidents WHERE ticket_id=?', (row['ticket_id'],)).fetchone())
                conn.execute('''INSERT INTO incident_events(ticket_id,actor_email,actor_role,event,note,
                    before_state,after_state,request_id,source_alert,created_at)
                    VALUES(?,?,?,'resolved',?,?,?,?,?,COALESCE(?,CURRENT_TIMESTAMP))''',
                    (row['ticket_id'], actor, actor_role, reason, json.dumps(before), json.dumps(after),
                     'migration:employee-report:' + row['employee_report_id'], row['proxy_alert_id'], timestamp))
            conn.execute('UPDATE incidents SET historical_import=0 WHERE ticket_id=?', (row['ticket_id'],))


def change(ticket_id, identity, *, status=None, note=None, assignee=None, resolution=None):
    if note is not None and not isinstance(note, str):
        raise ValueError('Reason must be text.')
    note = (note or '').strip()
    if status not in (None, 'open', 'closed') or len(note) > 1000:
        raise ValueError('Invalid status or note.')
    if status is None and assignee is None:
        raise ValueError('Send a status or assignee.')
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        record = conn.execute('SELECT * FROM incidents WHERE ticket_id=?', (ticket_id,)).fetchone()
        if not record:
            return None
        before = dict(record)
        owner = before.get('assigned_to')
        if owner and owner.lower() != identity.email.lower():
            raise IncidentConflict('Another SOC analyst owns this incident. Ask its owner to unassign it.')
        events = []
        request_id = f'incident:{ticket_id}'
        if assignee is not None:
            if assignee not in ('me', ''):
                raise ValueError("Assignee must be 'me' or empty.")
            new_owner = identity.email if assignee == 'me' else None
            if new_owner != owner:
                conn.execute('UPDATE incidents SET assigned_to=? WHERE ticket_id=?', (new_owner, ticket_id))
                events.append(('assigned' if new_owner else 'unassigned', new_owner))
            owner = new_owner
        if status == 'closed' and before['status'] != 'closed':
            if owner != identity.email:
                raise IncidentConflict('Assign the incident to yourself before resolving it.')
            if len(note) < 5:
                raise ValueError('Add a reason of at least 5 characters.')
            if before.get('reported_url'):
                if resolution not in ('block', 'allow'):
                    raise ValueError('Choose Block or Allow to resolve a link incident.')
                revision = conn.execute("SELECT count(*) FROM incident_events WHERE ticket_id=? AND event='resolved'", (ticket_id,)).fetchone()[0] + 1
                request_id = f'incident:{ticket_id}:resolve:{revision}'
                proxy_service.manual_decision(domain_value=before['reported_url'], action=resolution,
                    reason=note, identity=identity, request_id=request_id, alert_id=before.get('proxy_alert_id'))
            else:
                resolution = 'reviewed'
            conn.execute('''UPDATE incidents SET status='closed',closed_at=CURRENT_TIMESTAMP,
                resolution=?,resolution_reason=?,resolved_by=? WHERE ticket_id=?''',
                (resolution, note, identity.email, ticket_id))
            events.append(('resolved', note))
        elif status == 'open' and before['status'] == 'closed':
            conn.execute("UPDATE incidents SET status='open',closed_at=NULL WHERE ticket_id=?", (ticket_id,))
            events.append(('reopened', note or 'Reopened for review; current proxy policy remains in effect.'))
        after = dict(conn.execute('SELECT * FROM incidents WHERE ticket_id=?', (ticket_id,)).fetchone())
        for event, event_note in events:
            conn.execute('''INSERT INTO incident_events(ticket_id,actor_email,actor_role,event,note,
                before_state,after_state,request_id,source_alert) VALUES(?,?,?,?,?,?,?,?,?)''',
                (ticket_id, identity.email, identity.role, event, event_note, json.dumps(before),
                 json.dumps(after), request_id, before.get('proxy_alert_id')))
    proxy_store.publish_alert({'type': 'incident.updated', 'ticketId': ticket_id})
    return after
