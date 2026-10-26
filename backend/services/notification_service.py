"""Durable, deduplicated SMTP outbox; OTP remains synchronous and independent."""
import html
import logging
import os
import time
import uuid
from contextlib import closing

import database
from services.email_service import EmailService

logger = logging.getLogger(__name__)


def education_cooldown():
    return max(3600, int(os.environ.get('EDUCATION_COOLDOWN_SECONDS', '86400')))


def education_delivery(conn, recipient):
    """One recipient-wide delivery state for baseline and assessment follow-ups."""
    row = conn.execute('''SELECT n.id,n.sent_at,n.last_error,n.attempts,n.created_at,
        CASE WHEN n.dedupe_key LIKE 'training:exam:%' THEN 'training' ELSE 'baseline' END AS kind,
        a.actor_role,
        MAX(COALESCE(CAST(strftime('%s',n.sent_at) AS INTEGER),0),
            COALESCE(CAST(strftime('%s',n.created_at) AS INTEGER),0)) AS epoch
        FROM notification_outbox n LEFT JOIN notification_audit a ON a.outbox_id=n.id
        WHERE lower(n.recipient)=lower(?)
        AND (n.dedupe_key LIKE 'education:%' OR n.dedupe_key LIKE 'training:exam:%')
        ORDER BY CASE WHEN n.last_error='skipped_not_eligible' THEN 2
            WHEN n.sent_at IS NULL THEN 0 ELSE 1 END,epoch DESC,n.id DESC LIMIT 1''',
        (recipient,)).fetchone()
    delivery = dict(row) if row else None
    cancelled = row and row['last_error'] == 'skipped_not_eligible'
    pending = row and row['sent_at'] is None and not cancelled
    cooldown_until = row['epoch'] + education_cooldown() if row and not cancelled and not pending else None
    return {'delivery': delivery, 'canSend': not pending and (cooldown_until is None or cooldown_until <= int(time.time())),
            'cooldownUntil': cooldown_until}


def security_inbox():
    threshold = int(os.environ.get('EDUCATION_SCORE_THRESHOLD', '60'))
    with closing(database.get_connection()) as conn:
        employees = [dict(row) for row in conn.execute('''SELECT a.id, a.email, u.divisi, u.points
            FROM employee_accounts a JOIN user_history u ON lower(a.email)=lower(u.email)
            WHERE a.role='employee' AND a.is_active=1 AND u.points < ?
            ORDER BY u.points, a.email''', (threshold,)).fetchall()]
        for employee in employees:
            employee.update(education_delivery(conn, employee['email']))
        reports = [dict(row) for row in conn.execute('''SELECT * FROM employee_url_reports
            WHERE report_type='url' ORDER BY created_at DESC, id LIMIT 100''').fetchall()]
        audit = [dict(row) for row in conn.execute('''SELECT a.*,n.sent_at,n.last_error,n.attempts,
            CASE WHEN n.dedupe_key LIKE 'training:exam:%' THEN 'training' ELSE 'baseline' END AS kind
            FROM notification_audit a JOIN notification_outbox n ON n.id=a.outbox_id
            ORDER BY a.id DESC LIMIT 30''').fetchall()]
    # Evidence does not mutate proxy policies; only an explicit SOC action does.
    from services.report_service import _serialized
    reports = [_serialized(report) for report in reports]
    return {'threshold': threshold, 'scoreScale': 200, 'employees': employees,
            'reports': reports, 'audit': audit, 'deliveryMode': 'Mailpit (lab)',
            'emailEnabled': os.environ.get('EDUCATION_EMAIL_ENABLED', 'true').lower() == 'true',
            'automatic': os.environ.get('EDUCATION_AUTO_ENABLED', 'false').lower() == 'true'}


def queue_manual_warning(identity, account_id, reason, request_id):
    if identity.role != 'soc':
        raise PermissionError('Only SOC can send a baseline warning')
    if os.environ.get('EDUCATION_EMAIL_ENABLED', 'true').lower() != 'true':
        raise ValueError('Pengiriman warning sedang dinonaktifkan')
    if not isinstance(account_id, int) or isinstance(account_id, bool):
        raise ValueError('accountId wajib berupa integer')
    if not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 1000:
        raise ValueError('Alasan warning wajib 5–1000 karakter')
    threshold = int(os.environ.get('EDUCATION_SCORE_THRESHOLD', '60'))
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT a.email, u.points FROM employee_accounts a
            JOIN user_history u ON lower(a.email)=lower(u.email)
            WHERE a.id=? AND a.role='employee' AND a.is_active=1 AND u.points < ?''',
            (account_id, threshold)).fetchone()
        if not row:
            raise ValueError('Penerima harus employee aktif dengan poin di bawah baseline')
        if not education_delivery(conn, row['email'])['canSend']:
            raise ValueError('A security education email is already queued or was sent recently. Refresh the inbox and wait for the shared cooldown.')
        text = (f"Skor pembelajaran Anda {row['points']}/200, di bawah baseline {threshold}/200. "
                f"Pesan tim {identity.role.upper()}: {reason.strip()}\n\n"
                'Lanjutkan training, Spot the Fake, dan kuis harian di dashboard Afferent Reflex. '
                'Periksa domain, jangan bagikan OTP/password, dan laporkan link meragukan.')
        outbox = conn.execute('''INSERT INTO notification_outbox
            (dedupe_key, recipient, subject, text_body) VALUES (?, ?, ?, ?)''',
            (f"education:{row['email']}:{request_id}", row['email'], 'Afferent Reflex — warning edukasi keamanan', text))
        conn.execute('''INSERT INTO notification_audit
            (actor_email, actor_role, recipient, score, reason, request_id, outbox_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (identity.email, identity.role, row['email'], row['points'], reason.strip(), request_id, outbox.lastrowid))
    return {'queued': True, 'outboxId': outbox.lastrowid, 'deliveryMode': 'Mailpit (lab)'}


def enqueue(recipient, subject, text, dedupe_key):
    if not recipient:
        return
    with closing(database.get_connection()) as conn, conn:
        conn.execute('INSERT OR IGNORE INTO notification_outbox (dedupe_key, recipient, subject, text_body) VALUES (?, ?, ?, ?)',
                     (dedupe_key, recipient, subject, text))


def queue_education():
    threshold = int(os.environ.get('EDUCATION_SCORE_THRESHOLD', '60'))
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        rows = conn.execute('''SELECT a.email, u.points, u.click_count, u.viewed_training_count
            FROM employee_accounts a JOIN user_history u ON lower(u.email)=lower(a.email)
            WHERE a.role='employee' AND a.is_active=1 AND u.points < ?''', (threshold,)).fetchall()
        for row in rows:
            if not education_delivery(conn, row['email'])['canSend']:
                continue
            text = (f"Skor pembelajaran Anda saat ini {row['points']}/200. "
                    f"Tercatat {row['click_count']} klik simulasi dan {row['viewed_training_count']} training selesai. "
                    'Luangkan waktu untuk training, Spot the Fake, dan kuis harian. '
                    'Periksa domain sebelum membuka link, jangan bagikan OTP/password, '
                    'dan laporkan link yang meragukan melalui dashboard Afferent Reflex.')
            conn.execute('''INSERT INTO notification_outbox (dedupe_key,recipient,subject,text_body)
                VALUES (?,?,?,?)''', (f"education:{row['email']}:auto:{uuid.uuid4().hex}",
                row['email'], 'Afferent Reflex — edukasi keamanan personal', text))


def deliver_one():
    now = int(time.time())
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT * FROM notification_outbox WHERE sent_at IS NULL
            AND available_at <= ? AND lease_until <= ? ORDER BY id LIMIT 1''', (now, now)).fetchone()
        if not row:
            return False
        conn.execute('UPDATE notification_outbox SET lease_until=?, attempts=attempts+1 WHERE id=?', (now + 120, row['id']))
    try:
        # Re-check eligibility at delivery time: recovered scores must not warn.
        with closing(database.get_connection()) as conn:
            eligible = conn.execute('''SELECT 1 FROM employee_accounts a JOIN user_history u
                ON lower(u.email)=lower(a.email) WHERE a.email=? AND a.is_active=1
                AND a.role='employee' AND u.points < ?''',
                (row['recipient'], int(os.environ.get('EDUCATION_SCORE_THRESHOLD', '60')))).fetchone()
            if row['dedupe_key'].startswith('training:exam:'):
                eligible = conn.execute('''SELECT 1 FROM learning_exams e JOIN employee_accounts a
                    ON a.id=e.account_id WHERE e.id=? AND e.status='completed' AND e.needs_training=1
                    AND a.email=? AND a.is_active=1 AND a.role='employee' ''',
                    (row['dedupe_key'].removeprefix('training:exam:'), row['recipient'])).fetchone()
        if not eligible:
            with closing(database.get_connection()) as conn, conn:
                conn.execute("UPDATE notification_outbox SET sent_at=CURRENT_TIMESTAMP, last_error='skipped_not_eligible', lease_until=0 WHERE id=?", (row['id'],))
            return True
        EmailService().send(to_address=row['recipient'], subject=row['subject'], text=row['text_body'],
                            html='<div style="font-family:Poppins,Arial,sans-serif;line-height:1.7"><h2>Afferent Reflex Security</h2><p>' + html.escape(row['text_body']) + '</p></div>')
    except Exception as exc:
        # SMTP acceptance followed by a crash may replay a message: at-least-once,
        # not exactly-once. No tokens, provider responses, or recipient logged.
        logger.warning('Notification delivery deferred: %s', type(exc).__name__)
        with closing(database.get_connection()) as conn, conn:
            conn.execute('UPDATE notification_outbox SET lease_until=0, available_at=?, last_error=? WHERE id=?',
                         (now + min(3600, 30 * 2 ** min(row['attempts'], 7)), type(exc).__name__, row['id']))
        return False
    with closing(database.get_connection()) as conn, conn:
        conn.execute('UPDATE notification_outbox SET sent_at=CURRENT_TIMESTAMP, lease_until=0, last_error=NULL WHERE id=?', (row['id'],))
    return True
