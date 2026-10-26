"""Cross-inbox email coordination; temporary DB, no real SMTP or campaign."""
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

import test_technical_debt  # establishes the isolated database before app import
import database
from services import auth_service, exam_service, notification_service as notifications


class NotificationCoordination(unittest.TestCase):
    def setUp(self):
        self.email = f'notification-{uuid.uuid4().hex}@demo.test'
        account = auth_service.create_account(email=self.email, password='NotificationTesting2026!', role='employee', division='IT')
        self.employee = SimpleNamespace(account_id=account['id'])
        self.account_id = account['id']
        self.admin = SimpleNamespace(role='phishing_admin', email='admin@demo.test')
        self.soc = SimpleNamespace(role='soc', email='soc@demo.test')
        database.adjust_points(self.email, 'IT', -50)
        with closing(database.get_connection()) as conn, conn:
            exam_service.require_for_click(conn, self.email, uuid.uuid4().hex, 50)
        self.exam = exam_service.current(self.employee)
        exam_service.act(self.employee, self.exam['id'], 'start', {})
        exam_service.act(self.employee, self.exam['id'], 'submit', {'answers': [(q[2] + 1) % 3 for q in exam_service.QUESTIONS]})

    def warning(self):
        return notifications.queue_manual_warning(self.soc, self.account_id, 'Review phishing guidance.', uuid.uuid4().hex)

    def training(self):
        return exam_service.queue_training(self.admin, self.exam['id'], 'Review the phishing assessment.', uuid.uuid4().hex)

    def delivery(self):
        with closing(database.get_connection()) as conn:
            return notifications.education_delivery(conn, self.email)

    def count(self):
        with closing(database.get_connection()) as conn:
            return conn.execute('SELECT count(*) FROM notification_outbox WHERE recipient=?', (self.email,)).fetchone()[0]

    def test_admin_queue_and_delivery_are_visible_to_soc_and_block_another_email(self):
        queued = self.training()
        employee = next(e for e in notifications.security_inbox()['employees'] if e['email'] == self.email)
        self.assertFalse(employee['canSend'])
        self.assertEqual((employee['delivery']['kind'], employee['delivery']['actor_role']), ('training', 'phishing_admin'))
        with self.assertRaises(ValueError):
            self.warning()
        notifications.queue_education()
        self.assertEqual(self.count(), 1)
        with patch.object(notifications.EmailService, 'send') as send:
            while notifications.deliver_one():
                pass
            self.assertEqual(sum(c.kwargs['to_address'] == self.email for c in send.call_args_list), 1)
        delivery = self.delivery()
        self.assertIsNotNone(delivery['delivery']['sent_at'])
        self.assertFalse(delivery['canSend'])
        with self.assertRaises(ValueError):
            self.warning()
        self.assertEqual(self.training()['outboxId'], queued['outboxId'])
        audit = next(a for a in notifications.security_inbox()['audit'] if a['recipient'] == self.email)
        self.assertIsNotNone(audit['sent_at'])

    def test_soc_warning_blocks_admin_then_cooldown_allows_follow_up(self):
        queued = self.warning()
        assessment = next(a for a in exam_service.inbox()['assessments'] if a['id'] == self.exam['id'])
        self.assertFalse(assessment['canSend'])
        self.assertEqual(assessment['delivery']['actor_role'], 'soc')
        with self.assertRaises(ValueError):
            self.training()
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE notification_outbox SET created_at=datetime('now','-2 days'),sent_at=datetime('now','-2 days') WHERE id=?", (queued['outboxId'],))
        self.assertTrue(self.delivery()['canSend'])
        self.training()
        self.assertEqual(self.count(), 2)

    def test_cooldown_uses_actual_delivery_time_after_a_delayed_send(self):
        queued = self.warning()
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE notification_outbox SET created_at=datetime('now','-2 days'),sent_at=CURRENT_TIMESTAMP WHERE id=?", (queued['outboxId'],))
        self.assertFalse(self.delivery()['canSend'])
        with self.assertRaises(ValueError):
            self.training()

    def test_retrying_email_keeps_both_paths_locked_even_after_a_day(self):
        queued = self.training()
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE notification_outbox SET created_at=datetime('now','-2 days'),last_error='SMTPUnavailable' WHERE id=?", (queued['outboxId'],))
        self.assertFalse(self.delivery()['canSend'])
        with self.assertRaises(ValueError):
            self.warning()

    def test_cancelled_send_does_not_count_as_delivery_or_hide_a_recent_send(self):
        queued = self.warning()
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE notification_outbox SET sent_at=CURRENT_TIMESTAMP,last_error='skipped_not_eligible' WHERE id=?", (queued['outboxId'],))
        self.assertTrue(self.delivery()['canSend'])
        training = self.training()
        with closing(database.get_connection()) as conn, conn:
            conn.execute('UPDATE notification_outbox SET sent_at=CURRENT_TIMESTAMP WHERE id=?', (training['outboxId'],))
            conn.execute("INSERT INTO notification_outbox(dedupe_key,recipient,subject,text_body,sent_at,last_error) VALUES(?,?,?, ?,CURRENT_TIMESTAMP,'skipped_not_eligible')",
                         ('education:cancelled:' + uuid.uuid4().hex, self.email, 'Fixture', 'Fixture'))
        self.assertFalse(self.delivery()['canSend'])
        self.assertEqual(self.delivery()['delivery']['id'], training['outboxId'])

    def test_concurrent_admin_and_soc_approval_create_only_one_email(self):
        barrier = Barrier(2)

        def attempt(action):
            barrier.wait(timeout=10)
            try:
                action()
                return 'queued'
            except ValueError:
                return 'blocked'

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [self.training, self.warning]))
        self.assertCountEqual(results, ['queued', 'blocked'])
        self.assertEqual(self.count(), 1)
