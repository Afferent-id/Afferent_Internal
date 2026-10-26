"""Campaign-triggered assessment; answer keys and grading stay on the server."""
import json
import os
import secrets
import time
from contextlib import closing
import database
from services.notification_service import education_delivery

# Keep old versions immutable: completed assessments retain their original grade.
QUESTIONS = (
 ('An email says your account will close in 10 minutes. What should you do?', ['Click immediately','Verify through a known company channel','Reply with your password'],1),
 ('Which address belongs to example.com?', ['example.com.attacker.net','example-login.net','accounts.example.com'],2),
 ('A padlock or HTTPS means a website is always trustworthy.', ['True','False','Only on a work laptop'],1),
 ('An unexpected attachment asks you to enable macros. What is safest?', ['Enable macros','Forward it to colleagues','Do not open it; report it'],2),
 ('A caller claiming to be IT asks for your OTP. What should you do?', ['Refuse and verify independently','Share it once','Send a screenshot of the OTP'],0),
 ('The sender display name says CEO. What else should you check?', ['Only the logo','The full sender address and request','The font size'],1),
 ('You entered a password on a suspicious page. What next?', ['Wait for an email','Delete browser history only','Notify security and change it through the official site'],2),
 ('How should you inspect an unfamiliar link?', ['Check its actual destination before opening','Trust the button text','Open it to see if it looks professional'],0),
 ('A supplier changes its bank account by email. What should you do?', ['Pay quickly','Verify using a previously known phone number','Use the number in that email only'],1),
 ('What is a safer way to reach your company login?', ['Use any urgent email link','Search advertisements','Use a saved official bookmark or known address'],2),
 ('What should a suspicious-link report contain?', ['The link and context, without passwords or OTPs','Your password','Private session tokens'],0),
 ('A familiar email asks for an unusual action. Is it safe?', ['Always','Verify first; accounts and threads can be compromised','Yes if it contains your name'],1),
 ('A QR code opens a login page. What should you check?', ['Only its design','Nothing; QR codes are safe','The domain and whether the request was expected'],2),
 ('Which practice reduces account compromise?', ['Unique passwords and multi-factor authentication','One password for every service','Sharing passwords with teammates'],0),
 ('You clicked a suspicious link but entered nothing. What next?', ['Ignore it','Report it promptly and follow security guidance','Send the link to everyone'],1),
)


def init_schema(conn):
    conn.executescript('''CREATE TABLE IF NOT EXISTS learning_exams (
        id TEXT PRIMARY KEY,account_id INTEGER NOT NULL,campaign_id TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,trigger_score INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'required' CHECK(status IN ('required','started','completed')),
        started_at TEXT,completed_at TEXT,answers_json TEXT,correct INTEGER,percent REAL,
        needs_training INTEGER NOT NULL DEFAULT 0,pass_percent INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(account_id,campaign_id));
        CREATE INDEX IF NOT EXISTS idx_exam_queue ON learning_exams(account_id,status);
        CREATE TABLE IF NOT EXISTS exam_violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,exam_id TEXT NOT NULL,kind TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TRIGGER IF NOT EXISTS exam_violation_no_update BEFORE UPDATE ON exam_violations
        BEGIN SELECT RAISE(ABORT,'Exam observations are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS exam_violation_no_delete BEFORE DELETE ON exam_violations
        BEGIN SELECT RAISE(ABORT,'Exam observations are append-only'); END;
        CREATE TABLE IF NOT EXISTS exam_campaign_sync (account_id INTEGER PRIMARY KEY,checked_at INTEGER NOT NULL);''')


def require_for_click(conn, email, campaign_id, score):
    if score >= int(os.environ.get('EXAM_SCORE_THRESHOLD','60')) or not campaign_id:
        return
    account = conn.execute("SELECT id FROM employee_accounts WHERE email=? COLLATE NOCASE AND role='employee' AND is_active=1", (email,)).fetchone()
    if account:
        conn.execute('''INSERT OR IGNORE INTO learning_exams
            (id,account_id,campaign_id,trigger_score,pass_percent) VALUES(?,?,?,?,?)''',
            (secrets.token_hex(16),account['id'],campaign_id,score,int(os.environ.get('EXAM_PASS_PERCENT','80'))))


def sync_campaigns(identity):
    """Verify clicks through GoPhish, never an employee-supplied email or RID."""
    now = int(time.time())
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        prior = conn.execute('SELECT checked_at FROM exam_campaign_sync WHERE account_id=?',(identity.account_id,)).fetchone()
        if prior and prior['checked_at'] > now - 10:
            return
        conn.execute('INSERT OR REPLACE INTO exam_campaign_sync VALUES(?,?)',(identity.account_id,now))
    import gophish_client
    for campaign in gophish_client.get_campaigns():
        database.sync_gophish_events(campaign)


def serialize(row):
    return {key:row[key] for key in ('id','campaign_id','trigger_score','status','correct','percent','needs_training','pass_percent','created_at','completed_at')}


def current(identity):
    with closing(database.get_connection()) as conn:
        row = conn.execute("SELECT * FROM learning_exams WHERE account_id=? AND status!='completed' ORDER BY created_at,id LIMIT 1",(identity.account_id,)).fetchone()
    return serialize(row) if row else None


def act(identity, exam_id, action, body):
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM learning_exams WHERE id=? AND account_id=?',(exam_id,identity.account_id)).fetchone()
        if not row:
            raise ValueError('Assessment was not found.')
        if action == 'start' and row['status'] != 'completed':
            conn.execute("UPDATE learning_exams SET status='started',started_at=COALESCE(started_at,CURRENT_TIMESTAMP) WHERE id=?",(exam_id,))
            return {'questions':[{'id':i,'question':q[0],'options':q[1]} for i,q in enumerate(QUESTIONS)],'examId':exam_id}
        if action == 'violation':
            kind = body.get('kind')
            if kind not in ('tab_hidden','window_blur','fullscreen_exit','copy','cut','paste','context_menu'):
                raise ValueError('Invalid observation.')
            if row['status'] != 'started':
                raise ValueError('Start the assessment first.')
            count = conn.execute('SELECT count(*) FROM exam_violations WHERE exam_id=?',(exam_id,)).fetchone()[0]
            if count < 100:
                conn.execute('INSERT INTO exam_violations(exam_id,kind) VALUES(?,?)',(exam_id,kind))
            return {'recorded':count < 100}
        if action == 'submit' and row['status'] != 'completed':
            answers = body.get('answers')
            if row['status'] != 'started' or not isinstance(answers,list) or len(answers)!=len(QUESTIONS) or any(type(a) is not int or a not in range(3) for a in answers):
                raise ValueError('Answer all 15 questions before submitting.')
            correct = sum(a==q[2] for a,q in zip(answers,QUESTIONS))
            percent = round(correct*100/len(QUESTIONS),2)
            conn.execute('''UPDATE learning_exams SET status='completed',completed_at=CURRENT_TIMESTAMP,
                answers_json=?,correct=?,percent=?,needs_training=? WHERE id=?''',
                (json.dumps(answers),correct,percent,int(percent < row['pass_percent']),exam_id))
        elif action not in ('submit','start'):
            raise ValueError('Invalid assessment action.')
        return {'result':serialize(conn.execute('SELECT * FROM learning_exams WHERE id=?',(exam_id,)).fetchone())}


def inbox():
    with closing(database.get_connection()) as conn:
        rows = conn.execute('''SELECT e.*,a.email,COALESCE(u.divisi,'General') AS division,
            (SELECT count(*) FROM exam_violations v WHERE v.exam_id=e.id) AS observations,
            n.id AS outbox_id,n.sent_at,n.last_error
            FROM learning_exams e JOIN employee_accounts a ON a.id=e.account_id
            LEFT JOIN user_history u ON lower(u.email)=lower(a.email)
            LEFT JOIN notification_outbox n ON n.dedupe_key='training:exam:'||e.id
            ORDER BY e.needs_training DESC,e.created_at DESC LIMIT 100''').fetchall()
        logs = conn.execute('''SELECT v.exam_id,v.kind,v.created_at FROM exam_violations v
            WHERE v.exam_id IN (SELECT id FROM learning_exams ORDER BY created_at DESC LIMIT 100) ORDER BY v.id''').fetchall()
        deliveries = {email: education_delivery(conn, email) for email in {r['email'] for r in rows}}
    return {'assessments':[{**serialize(r),'email':r['email'],'division':r['division'],
        'observations':r['observations'],'observationLog':[dict(v) for v in logs if v['exam_id']==r['id']],
        'outboxId':r['outbox_id'],'sentAt':r['sent_at'],'deliveryError':r['last_error'],
        'delivery':deliveries[r['email']]['delivery'],
        'canSend':bool(r['status']=='completed' and r['needs_training'] and not r['outbox_id']
            and deliveries[r['email']]['canSend'] and os.environ.get('EDUCATION_EMAIL_ENABLED','true').lower()=='true')}
        for r in rows]}


def queue_training(identity, exam_id, reason, request_id):
    if identity.role != 'phishing_admin':
        raise PermissionError('Only the administrator can recommend training.')
    if os.environ.get('EDUCATION_EMAIL_ENABLED', 'true').lower() != 'true':
        raise ValueError('Education email delivery is disabled in the server configuration.')
    if not isinstance(reason,str) or not 5 <= len(reason.strip()) <= 1000:
        raise ValueError('Add a recommendation of 5–1000 characters.')
    with closing(database.get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('''SELECT e.*,a.email FROM learning_exams e JOIN employee_accounts a ON a.id=e.account_id
            WHERE e.id=? AND e.status='completed' AND e.needs_training=1 AND a.role='employee' AND a.is_active=1''',(exam_id,)).fetchone()
        if not row:
            raise ValueError('Only completed assessments below the pass threshold qualify.')
        key = f'training:exam:{exam_id}'
        previous = conn.execute('SELECT id FROM notification_outbox WHERE dedupe_key=?',(key,)).fetchone()
        if previous:
            return {'queued':True,'duplicate':True,'outboxId':previous['id']}
        if not education_delivery(conn, row['email'])['canSend']:
            raise ValueError('A security education email is already queued or was sent recently. Refresh the inbox and wait for the shared cooldown.')
        text = (f"Your phishing assessment score is {row['percent']:g}% ({row['correct']}/15). "
            f"The pass threshold is {row['pass_percent']}%.\n\n{reason.strip()}\n\n"
            'Please complete the security training recommended by your administrator. '
            'Review sender addresses, verify unexpected requests and never share passwords or OTPs.')
        outbox = conn.execute('INSERT INTO notification_outbox(dedupe_key,recipient,subject,text_body) VALUES(?,?,?,?)',
            (key,row['email'],'Afferent Reflex — your security training recommendation',text))
        conn.execute('''INSERT INTO notification_audit(actor_email,actor_role,recipient,score,reason,request_id,outbox_id)
            VALUES(?,?,?,?,?,?,?)''',(identity.email,identity.role,row['email'],row['trigger_score'],reason.strip(),request_id,outbox.lastrowid))
        return {'queued':True,'outboxId':outbox.lastrowid}
