"""Incident handling is audited: who resolved, reopened or assigned, when, and why."""
import unittest
import unittest.mock
import uuid

import test_technical_debt  # noqa: F401  (sets the same safe test environment as the other suites)
from test_technical_debt import login
from app import app
import database
from services import auth_service


def make_account(role):
    email = uuid.uuid4().hex + '@demo.test'
    password = 'IncidentAuditTesting2026!'
    auth_service.create_account(email=email, password=password, role=role, division='IT')
    return email, {'X-Afferent-Session': login(email, password)}


class IncidentAudit(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.soc_email,self.soc = make_account('soc')
        _,self.other_soc = make_account('soc')
        _,self.admin = make_account('phishing_admin')
        _,self.employee = make_account('employee')
        self.ticket = 'INC-'+uuid.uuid4().hex
        database.create_incident(ticket_id=self.ticket,source_type='real_world_report',divisi='Finance',
            severity='low',reported_url='https://review.example.test',vt_verdict='malicious')
        policy = unittest.mock.patch('services.incident_service.proxy_service.manual_decision')
        self.policy = policy.start()
        self.addCleanup(policy.stop)

    def patch(self,body,headers=None,ticket=None):
        return self.client.patch(f'/api/incidents/{ticket or self.ticket}',json=body,headers=headers or self.soc)

    def events(self,headers=None):
        return self.client.get(f'/api/incidents/{self.ticket}/events',headers=headers or self.soc)

    def test_owner_reason_and_policy_required(self):
        self.assertEqual(self.patch({'status':'closed','note':'Confirmed harmless.','resolution':'allow'}).status_code,409)
        self.assertEqual(self.patch({'assignee':'me'}).status_code,200)
        self.assertEqual(self.patch({'status':'closed','note':'ok','resolution':'allow'}).status_code,400)
        self.assertEqual(self.patch({'status':'closed','note':'Confirmed harmless.'}).status_code,400)
        response = self.patch({'status':'closed','note':'Confirmed harmless.','resolution':'allow'})
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(self.policy.call_args.kwargs['action'],'allow')
        event = self.events().get_json()['events'][0]
        self.assertEqual((event['event'],event['actor_email'],event['actor_role']),('resolved',self.soc_email,'soc'))
        self.assertTrue(event['created_at'])

    def test_reopen_keeps_policy_and_resolution_is_idempotent(self):
        self.patch({'assignee':'me'})
        body = {'status':'closed','note':'Confirmed phishing.','resolution':'block'}
        self.assertEqual(self.patch(body).status_code,200)
        self.assertEqual(self.patch(body).status_code,200)
        self.assertEqual(self.policy.call_count,1)
        response = self.patch({'status':'open','note':'More evidence needs review.'})
        self.assertEqual(response.status_code,200)
        self.assertIsNone(response.get_json()['incident']['closed_at'])
        self.assertEqual(self.policy.call_count,1)
        self.assertEqual([e['event'] for e in self.events().get_json()['events']],['reopened','resolved','assigned'])

    def test_assignment_cannot_be_stolen_and_no_op_is_not_logged(self):
        self.patch({'assignee':'me'});self.patch({'assignee':'me'})
        self.assertEqual(self.patch({'assignee':'me'},headers=self.other_soc).status_code,409)
        self.assertEqual(len(self.events().get_json()['events']),1)
        self.assertIsNone(self.patch({'assignee':''}).get_json()['incident']['assigned_to'])
        self.assertEqual(self.patch({'assignee':'someone@else.test'}).status_code,400)

    def test_validation_roles_and_not_found(self):
        self.assertEqual(self.patch({}).status_code,400)
        self.assertEqual(self.patch({'status':'maybe'}).status_code,400)
        self.assertEqual(self.patch({'status':'closed','note':'x'*1001}).status_code,400)
        self.assertEqual(self.patch({'status':'closed'},ticket='INC-MISSING').status_code,404)
        for headers in (self.admin,self.employee):
            self.assertEqual(self.patch({'assignee':'me'},headers=headers).status_code,403)
            self.assertEqual(self.events(headers=headers).status_code,403)
        self.assertEqual(self.client.patch(f'/api/incidents/{self.ticket}',json={'assignee':'me'}).status_code,401)


class SevereIncidentEmail(unittest.TestCase):
    def inbox_for(self, email):
        return [m for m in database.list_inbox_emails() if m['to_email'] == email]

    def test_high_severity_emails_active_soc_only(self):
        soc_email, _ = make_account('soc')
        employee_email, _ = make_account('employee')
        ticket = 'INC-' + uuid.uuid4().hex[:8].upper()
        database.create_incident(ticket_id=ticket, source_type='real_world_report', divisi='Finance <b>', severity='high', reported_url='http://x.example')
        mails = self.inbox_for(soc_email)
        self.assertEqual(len(mails), 1)
        self.assertIn(ticket, mails[0]['subject'])
        self.assertNotIn('<b>', mails[0]['body'].replace('<b>Ticket', '').replace('<b>Division', '').replace('<b>Reported', '').replace('</b>', ''))
        self.assertEqual(self.inbox_for(employee_email), [])

    def test_lower_severity_and_switch_send_nothing(self):
        soc_email, _ = make_account('soc')
        database.create_incident(ticket_id='INC-' + uuid.uuid4().hex[:8].upper(), source_type='real_world_report', divisi='IT', severity='medium')
        self.assertEqual(self.inbox_for(soc_email), [])
        with unittest.mock.patch.dict('os.environ', {'SEVERE_INCIDENT_EMAIL_ENABLED': 'false'}):
            database.create_incident(ticket_id='INC-' + uuid.uuid4().hex[:8].upper(), source_type='real_world_report', divisi='IT', severity='high')
        self.assertEqual(self.inbox_for(soc_email), [])

    def test_mail_failure_never_loses_the_ticket(self):
        ticket = 'INC-' + uuid.uuid4().hex[:8].upper()
        with unittest.mock.patch.object(database, 'create_inbox_email', side_effect=RuntimeError('smtp down')):
            database.create_incident(ticket_id=ticket, source_type='real_world_report', divisi='IT', severity='high')
        self.assertTrue(any(i['ticket_id'] == ticket for i in database.list_incidents()))


if __name__ == '__main__':
    unittest.main()
