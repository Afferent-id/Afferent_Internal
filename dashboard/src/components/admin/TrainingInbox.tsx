'use client';

import { useState } from 'react';
import { Mail, GraduationCap, RefreshCw } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import Dialog from '@/components/ui/Dialog';
import NotificationDelivery, { type EducationDelivery } from './NotificationDelivery';
import { useI18n } from '@/i18n/I18nProvider';

type Assessment = { id: string; email: string; division: string; status: string; trigger_score: number;
  percent: number | null; correct: number | null; pass_percent: number; needs_training: number;
  observations: number; observationLog: { kind: string; created_at: string }[];
  outboxId: number | null; sentAt: string | null; deliveryError: string | null;
  delivery: EducationDelivery | null; canSend: boolean };

export default function TrainingInbox() {
  const { t } = useI18n();
  const { data, error, isLoading, refresh } = usePolling<{ assessments: Assessment[] }>('/api/admin/training-inbox', 15000);
  const [selected, setSelected] = useState<Assessment | null>(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const [notice, setNotice] = useState('');
  const assessments = data?.assessments || [];
  const selectedState = assessments.find(item => item.id === selected?.id);
  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setFailure('');
    try {
      const response = await fetch('/api/admin/training-inbox', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ examId: selected.id, reason }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not queue the email. Please retry.');
      setNotice(body.duplicate ? 'This recommendation is already queued.' : 'Training recommendation queued for email delivery.');
      setSelected(null); refresh();
    } catch (err) { refresh(); setFailure(err instanceof Error ? err.message : 'Please retry.'); }
    finally { setBusy(false); }
  }
  return <section className="training-inbox">
    <div className="ops-head"><div><span className="eyebrow">Learning follow-up</span><h2>Training inbox</h2><p className="emp-muted">Review phishing assessments. Send recommendations when support is needed.</p></div><button className="btn" onClick={refresh}><RefreshCw size={16} />Refresh</button></div>
    <div className="strip"><span className="strip-static"><b>{assessments.filter(a => a.canSend).length}</b>Needs follow-up</span><span className="strip-static"><b>{assessments.filter(a => a.status !== 'completed').length}</b>Awaiting assessment</span><span className="strip-static"><b>{assessments.filter(a => a.sentAt && !a.deliveryError).length}</b>Recommendations sent</span></div>
    {notice && <p className="debt-notice" role="status">{notice}</p>}
    {error && <p className="debt-error" role="alert">Training inbox is unavailable. Please refresh.</p>}
    {isLoading && !data && <p role="status">Loading assessments…</p>}
    {data && !assessments.length && <div className="panel glass-card training-empty"><GraduationCap size={28} /><h3>No assessments yet</h3><p>A verified campaign click triggers an assessment when an employee’s score falls below 60/200.</p></div>}
    <div className="training-results">{assessments.map(item => <article key={item.id} className="panel glass-card training-result">
      <div className="ops-head"><div><h3>{item.email}</h3><p className="emp-muted">{item.division} · Campaign-click score {item.trigger_score}/200</p></div><span className="chip">{item.status === 'completed' ? item.needs_training ? 'Training recommended' : 'Passed' : 'Assessment pending'}</span></div>
      {item.status === 'completed' && <p className="training-grade">{item.percent}% <span>{item.correct}/15 correct · Pass {item.pass_percent}%</span></p>}
      <details className="provider-details"><summary>{item.observations} browser observations</summary><p className="emp-muted">Informational only. These events do not change the assessment score.</p>{item.observationLog.map((event, index) => <p key={index}>{event.kind.replaceAll('_', ' ')} · {event.created_at} UTC</p>)}</details>
      {(item.outboxId || Boolean(item.needs_training)) && <div className="emp-muted" role="status"><NotificationDelivery delivery={item.outboxId ? { sent_at: item.sentAt, last_error: item.deliveryError, kind: 'training', actor_role: 'phishing_admin' } : item.delivery} />{!item.outboxId && !item.canSend && item.delivery && <p>{t('inbox.delivery.cooldown')}</p>}</div>}
      {Boolean(item.needs_training) && !item.outboxId && <button className="btn btn-primary" disabled={!item.canSend} onClick={() => { setSelected(item); setReason(''); setFailure(''); }}><Mail size={16} />Send training recommendation</button>}
    </article>)}</div>
    <Dialog open={Boolean(selected)} onClose={() => !busy && setSelected(null)} busy={busy} title="Recommend security training" description={selected?.email} size="sm">
      <form className="debt-form" action="/api/admin/training-inbox" method="post" onSubmit={send}><label htmlFor="training-reason">Recommendation<textarea id="training-reason" name="reason" required minLength={5} maxLength={1000} rows={4} value={reason} onChange={e => setReason(e.target.value)} placeholder="What should this employee review?" /></label><p className="emp-muted">The email includes the assessment result and your recommendation.</p>{failure && <p className="debt-error" role="alert">{failure}</p>}<button className="btn btn-primary" disabled={busy || !selectedState?.canSend}>{busy ? 'Queuing…' : 'Send email'}</button></form>
    </Dialog>
  </section>;
}
