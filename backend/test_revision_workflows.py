"""Isolated regressions for VT queues, owned SOC resolution and learning assessments."""
import json
import sqlite3
import unittest
import uuid
from contextlib import closing
from unittest.mock import Mock, patch

from test_technical_debt import login
from app import app
import database
from routes import simulation_entry
import integrations
from services import auth_service, exam_service, incident_service, notification_service, proxy_store, report_service, url_scan_service


class RevisionWorkflows(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.password = 'RevisionTestingPassword2026!'
        self.identity, self.headers = self.account('employee')
        self.soc, self.soc_headers = self.account('soc')
        self.admin, self.admin_headers = self.account('phishing_admin')
        with closing(database.get_connection()) as conn, conn:
            conn.execute('UPDATE url_analysis_jobs SET done=1,lease_until=0')

    def account(self, role):
        email = f'{uuid.uuid4().hex}@demo.test'
        auth_service.create_account(email=email,password=self.password,role=role,division='IT')
        token = login(email,self.password)
        return auth_service.get_identity(token), {'X-Afferent-Session':token}

    def qualify(self):
        database.adjust_points(self.identity.email,'IT',-50)
        campaign = {'id':uuid.uuid4().hex,'timeline':[{'email':self.identity.email,'message':'Clicked Link'}]}
        database.sync_gophish_events(campaign)
        database.sync_gophish_events(campaign)
        return exam_service.current(self.identity)

    def test_retired_roles_cannot_create_login_or_reuse_sessions(self):
        for role in ('grc','ciso'):
            with self.assertRaises(auth_service.AuthError):
                auth_service.create_account(email=f'{uuid.uuid4().hex}@demo.test',password=self.password,role=role,division='IT')
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE employee_accounts SET role='grc' WHERE id=?",(self.identity.account_id,))
        self.assertIsNone(auth_service.get_identity(self.headers['X-Afferent-Session']))
        self.assertEqual(self.client.post('/api/auth/login',json={'email':self.identity.email,'password':self.password}).status_code,401)

    def test_campaign_gateway_routes_low_score_click_to_exam_without_issuing_identity(self):
        database.adjust_points(self.identity.email,'IT',-40)  # exactly 60 before the verified click
        rid = 'TestRID123'
        campaign = {'id':uuid.uuid4().hex,'results':[{'id':rid,'email':self.identity.email}],
            'timeline':[{'email':self.identity.email,'message':'Clicked Link'}]}
        upstream = Mock(status_code=200,content=b'<form></form>',headers={'Content-Type':'text/html'})
        with patch.dict('os.environ',{'SIMULATION_EDUCATION_URL':'http://dashboard.demo.test:3000/simulation/education'}),patch.object(simulation_entry.requests,'request',return_value=upstream) as forward,patch.object(simulation_entry.gophish_client,'get_campaigns',return_value=[campaign]):
            response = self.client.get('/simulation/entry?rid='+rid+'&url=http://127.0.0.1/private',headers=self.headers)
            self.assertEqual(response.status_code,302)
            self.assertEqual(response.headers['Location'],'http://dashboard.demo.test:3000/exam')
            exam = exam_service.current(self.identity)
            self.assertEqual((exam['trigger_score'], exam['status']), (50, 'required'))
            self.assertEqual(forward.call_args.kwargs['params'],{'rid':rid})
            self.assertFalse(forward.call_args.kwargs['allow_redirects'])
            anonymous = self.client.get('/simulation/entry?rid='+rid)
            self.assertEqual(anonymous.headers['Location'],'http://dashboard.demo.test:3000/simulation/education')
            self.assertNotIn('Set-Cookie',anonymous.headers)
        self.assertEqual(self.client.get('/simulation/entry?rid=bad').status_code,400)

    def test_campaign_gateway_preserves_landing_and_never_forwards_password_fields(self):
        rid = 'TestRID456'
        campaign = {'id':uuid.uuid4().hex,'results':[{'id':rid,'email':self.identity.email}],
            'timeline':[{'email':self.identity.email,'message':'Clicked Link'}]}
        upstream = Mock(status_code=200,content=b'<form>Demo</form>',headers={'Content-Type':'text/html'})
        with patch.dict('os.environ',{'SIMULATION_EDUCATION_URL':'http://dashboard.demo.test:3000/simulation/education'}),patch.object(simulation_entry.requests,'request',return_value=upstream) as forward,patch.object(simulation_entry.gophish_client,'get_campaigns',return_value=[campaign]):
            self.assertEqual(self.client.get('/simulation/entry?rid='+rid).data,b'<form>Demo</form>')
            response = self.client.post('/simulation/entry?rid='+rid,data={'password':'must-never-be-forwarded','email':self.identity.email})
            self.assertEqual(response.status_code,303)
            self.assertEqual(forward.call_args.kwargs['data'],{})
        self.assertIsNone(exam_service.current(self.identity))

    def test_assessment_requires_verified_click_and_below_threshold(self):
        database.adjust_points(self.identity.email,'IT',-30)
        database.sync_gophish_events({'id':'boundary-'+uuid.uuid4().hex,'timeline':[{'email':self.identity.email,'message':'Clicked Link'}]})
        self.assertIsNone(exam_service.current(self.identity))  # exactly 60
        database.record_event(self.identity.email,'IT','clicked_link',campaign_id='untrusted-public-query')
        self.assertIsNone(exam_service.current(self.identity))
        exam = self.qualify()
        self.assertIsNotNone(exam)
        with closing(database.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM learning_exams WHERE account_id=?',(self.identity.account_id,)).fetchone()[0],1)
        other,_ = self.account('employee')
        with self.assertRaises(ValueError): exam_service.act(other,exam['id'],'start',{})

    def test_exam_grade_is_server_owned_single_submission_and_observations_append_only(self):
        exam = self.qualify()
        start = exam_service.act(self.identity,exam['id'],'start',{})
        self.assertEqual(len(start['questions']),15)
        self.assertNotIn('correct',json.dumps(start['questions']))
        with self.assertRaises(ValueError): exam_service.act(self.identity,exam['id'],'submit',{'answers':[0]*14,'percent':100})
        exam_service.act(self.identity,exam['id'],'violation',{'kind':'tab_hidden'})
        with closing(database.get_connection()) as conn:
            with self.assertRaises(sqlite3.IntegrityError): conn.execute("UPDATE exam_violations SET kind='copy' WHERE exam_id=?",(exam['id'],))
        answers = [q[2] if i < 12 else (q[2]+1)%3 for i,q in enumerate(exam_service.QUESTIONS)]
        result = exam_service.act(self.identity,exam['id'],'submit',{'answers':answers,'percent':0})['result']
        self.assertEqual((result['correct'],result['percent'],result['needs_training']),(12,80,0))
        retry = exam_service.act(self.identity,exam['id'],'submit',{'answers':[0]*15})['result']
        self.assertEqual(retry,result)
        self.assertIsNone(exam_service.current(self.identity))

    def test_training_requires_admin_approval_and_is_deduped_audited_and_delivered(self):
        exam = self.qualify()
        exam_service.act(self.identity,exam['id'],'start',{})
        result = exam_service.act(self.identity,exam['id'],'submit',{'answers':[q[2] if i<11 else (q[2]+1)%3 for i,q in enumerate(exam_service.QUESTIONS)]})['result']
        self.assertEqual(result['needs_training'],1)
        self.assertEqual(self.client.get('/api/admin/training-inbox',headers=self.headers).status_code,403)
        self.assertEqual(self.client.get('/api/admin/training-inbox',headers=self.soc_headers).status_code,403)
        with closing(database.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM notification_outbox WHERE dedupe_key=?',('training:exam:'+exam['id'],)).fetchone()[0],0)
        body = {'examId':exam['id'],'reason':'Review sender addresses and verification requests.'}
        self.assertEqual(self.client.post('/api/admin/training-inbox',json=body,headers=self.soc_headers).status_code,403)
        self.assertEqual(self.client.post('/api/admin/training-inbox',json=body,headers=self.admin_headers).status_code,202)
        duplicate = self.client.post('/api/admin/training-inbox',json=body,headers=self.admin_headers)
        self.assertTrue(duplicate.get_json()['duplicate'])
        database.adjust_points(self.identity.email,'IT',200)  # training is based on the completed exam
        with patch.object(notification_service.EmailService,'send') as send:
            for _ in range(50):
                if not notification_service.deliver_one(): break
            self.assertTrue(any(c.kwargs['to_address']==self.identity.email for c in send.call_args_list))
        with closing(database.get_connection()) as conn:
            row = conn.execute('SELECT * FROM notification_audit WHERE recipient=?',(self.identity.email,)).fetchone()
            self.assertEqual(row['actor_role'],'phishing_admin')
        own = next(r for r in exam_service.inbox()['assessments'] if r['id']==exam['id'])
        self.assertIsNotNone(own['sentAt'])

    def test_incident_ownership_policy_failure_and_audit(self):
        ticket = 'INC-'+uuid.uuid4().hex
        database.create_incident(ticket_id=ticket,source_type='real_world_report',divisi='IT',severity='low',reported_url='https://review.example.test/path')
        path = '/api/incidents/'+ticket
        body = {'status':'closed','resolution':'block','note':'Confirmed phishing domain.'}
        self.assertEqual(self.client.patch(path,json=body,headers=self.soc_headers).status_code,409)
        self.assertEqual(self.client.patch(path,json={'assignee':'me'},headers=self.soc_headers).status_code,200)
        other,other_headers = self.account('soc')
        self.assertEqual(self.client.patch(path,json={'assignee':'me'},headers=other_headers).status_code,409)
        with patch.object(incident_service.proxy_service,'manual_decision',side_effect=RuntimeError('policy database unavailable')):
            self.assertEqual(self.client.patch(path,json=body,headers=self.soc_headers).status_code,503)
        with closing(database.get_connection()) as conn:
            self.assertEqual(conn.execute('SELECT status FROM incidents WHERE ticket_id=?',(ticket,)).fetchone()['status'],'open')
        with patch.object(incident_service.proxy_service,'manual_decision') as decision:
            response = self.client.patch(path,json=body,headers=self.soc_headers)
            self.assertEqual(response.status_code,200,response.get_json())
            self.assertEqual(decision.call_args.kwargs['action'],'block')
            self.assertEqual(self.client.patch(path,json=body,headers=self.soc_headers).status_code,200)
            self.assertEqual(decision.call_count,1)
            self.assertEqual(self.client.patch(path,json={'status':'open'},headers=self.soc_headers).status_code,200)
            self.assertEqual(decision.call_count,1)
        with closing(database.get_connection()) as conn:
            event = conn.execute("SELECT * FROM incident_events WHERE ticket_id=? AND event='resolved'",(ticket,)).fetchone()
            self.assertEqual(event['actor_email'],self.soc.email)
            self.assertTrue(event['before_state']); self.assertTrue(event['after_state'])
            self.assertIn(':resolve:',event['request_id'])
            with self.assertRaises(sqlite3.IntegrityError): conn.execute('DELETE FROM incident_events WHERE id=?',(event['id'],))

    def test_url_lookup_404_submits_once_polls_and_scopes_results(self):
        url = 'https://'+uuid.uuid4().hex+'.example.test/path'
        miss = {'provider':'virustotal','success':False,'status_code':404}
        with patch.object(integrations,'scan_virustotal',return_value=miss), patch.object(integrations,'scan_urlscan',return_value={'provider':'urlscan','success':False,'status_code':404}):
            pending = report_service.analyze_url(url)
        self.assertTrue(pending['pending']); self.assertEqual(pending['verdict'],'unknown')
        url_scan_service.grant(self.identity,pending['scanId'])
        self.assertEqual(self.client.get('/api/threat/scan?scanId='+pending['scanId'],headers=self.soc_headers).status_code,403)
        other,_ = self.account('employee')
        self.assertIsNone(url_scan_service.result(other,pending['scanId']))
        with patch.object(integrations,'vt_file_request',return_value={'provider':'virustotal','success':True,'status_code':200,'data':{'data':{'id':'analysis-fixture'}}}) as submit:
            self.assertTrue(url_scan_service.process_one())
            self.assertEqual(submit.call_args.args,('POST','urls'))
            self.assertEqual(submit.call_args.kwargs['data'],{'url':url})
            self.assertFalse(url_scan_service.process_one())
        with closing(database.get_connection()) as conn, conn:
            conn.execute('UPDATE url_analysis_jobs SET available_at=0 WHERE id=?',(pending['scanId'],))
        response = {'provider':'virustotal','success':True,'status_code':200,'data':{'data':{'attributes':{'status':'completed','stats':{'malicious':8,'suspicious':0,'harmless':20,'undetected':2}}}}}
        with patch.object(integrations,'poll_vt_analysis',return_value=response),patch.object(incident_service.proxy_service,'manual_decision') as policy:
            self.assertTrue(url_scan_service.process_one())
            policy.assert_not_called()
        final = url_scan_service.result(self.identity,pending['scanId'])
        self.assertFalse(final['pending']); self.assertEqual(final['verdict'],'malicious')

    def test_migration_preserves_prior_soc_resolution_once_without_policy_writes(self):
        ticket = 'RPT-'+uuid.uuid4().hex
        database.create_incident(ticket_id=ticket,source_type='real_world_report',divisi='IT',severity='low',reported_url='https://historical.example.test')
        with closing(database.get_connection()) as conn, conn:
            conn.execute('UPDATE incidents SET employee_report_id=?,proxy_alert_id=?,historical_import=1 WHERE ticket_id=?',
                (uuid.uuid4().hex,str(uuid.uuid4()),ticket))
        prior = {'status':'allowed','actor_email':'historical-soc@demo.test','actor_role':'soc',
            'reason':'Previously reviewed and allowed.','decision_at':'2026-10-01 12:00:00'}
        with patch.object(proxy_store,'get_historical_report_resolution',return_value=prior),patch.object(incident_service.proxy_service,'manual_decision') as policy:
            incident_service.restore_historical_resolutions()
            incident_service.restore_historical_resolutions()
            policy.assert_not_called()
        with closing(database.get_connection()) as conn:
            row = conn.execute('SELECT * FROM incidents WHERE ticket_id=?',(ticket,)).fetchone()
            self.assertEqual((row['status'],row['resolution'],row['resolution_reason']),('closed','allow',prior['reason']))
            events = conn.execute('SELECT * FROM incident_events WHERE ticket_id=?',(ticket,)).fetchall()
            self.assertEqual(len(events),1)
            self.assertEqual(events[0]['created_at'],prior['decision_at'])


if __name__=='__main__': unittest.main()
