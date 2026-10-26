'use client';

import { FormEvent, useState } from 'react';
import { Flag, Mail, RefreshCw, History } from 'lucide-react';
import { usePolling } from '@/hooks/usePolling';
import ThreatEvidence, { EmployeeReport } from '../ThreatEvidence';
import AccessRequestsPanel from './AccessRequestsPanel';
import Dialog from '@/components/ui/Dialog';
import Field from '@/components/ui/Field';
import KpiCard from '@/components/ui/KpiCard';
import StateMessage from '@/components/ui/StateMessage';
import StatusChip from '@/components/ui/StatusChip';
import { useToast } from '@/components/ui/Toast';
import { useI18n } from '@/i18n/I18nProvider';
import type { MessageKey } from '@/i18n/messages';
import DataTable from '@/components/ui/DataTable';
import { useNow } from '@/hooks/useNow';
import { formatAgo } from '@/lib/relativeTime';

type Employee = { id: number; email: string; divisi: string; points: number; canSend: boolean;
  delivery: { sent_at: string | null; last_error: string | null; created_at: string; attempts: number } | null };
type Report = EmployeeReport;
type Audit = { id: number; actor_email: string; actor_role: string; recipient: string; score: number; reason: string; created_at: string };
type Inbox = { employees: Employee[]; reports: Report[]; audit: Audit[]; threshold: number; emailEnabled: boolean; automatic: boolean; deliveryMode: string };

type Tab = 'reports' | 'access' | 'employees' | 'audit';

export default function SecurityInboxSection({ canDecideAccess = false, onOpenIncidents }: { canDecideAccess?: boolean; onOpenIncidents?: () => void }) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const { data, error, isLoading, refresh } = usePolling<Inbox>('/api/admin/security-inbox', 10000);
  const [tab, setTab] = useState<Tab>('reports');
  const [selected, setSelected] = useState<Employee | null>(null);
  const [reason, setReason] = useState(() => t('inbox.dialog.default'));
  const [busy, setBusy] = useState(false);
  const [sendError, setSendError] = useState('');
  const [viewingReport, setViewingReport] = useState<Report | null>(null);
  const now = useNow();

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setSendError('');
    try {
      const res = await fetch('/api/admin/security-inbox', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ accountId: selected.id, reason }) });
      if (!res.ok) throw new Error('send');
      toast.show({ message: t('inbox.sent'), tone: 'ok' });
      setSelected(null); refresh();
    } catch { setSendError(t('inbox.err.send')); }
    finally { setBusy(false); }
  }

  const status = (value: string) => (['pending_review', 'open', 'resolved'].includes(value) ? t(`inbox.status.${value}` as MessageKey) : value.replaceAll('_', ' '));
  const delivery = (employee: Employee) => {
    const d = employee.delivery;
    if (!d) return t('inbox.emp.none');
    if (d.last_error === 'skipped_not_eligible') return t('inbox.emp.cancelled');
    if (d.sent_at) return t('inbox.emp.sent', { time: d.sent_at });
    return d.last_error ? t('inbox.emp.retry') : t('inbox.emp.queued');
  };
  const tabs: { id: Tab; label: string; icon: typeof Flag }[] = [
    { id: 'reports', label: t('inbox.tab.reports'), icon: Flag },
    { id: 'access', label: t('acc.tab'), icon: Flag },
    { id: 'employees', label: t('inbox.tab.warnings'), icon: Mail },
    { id: 'audit', label: t('inbox.tab.audit'), icon: History },
  ];

  return (
    <section className="ops-page" aria-label={t('inbox.title')}>
      <div className="exec-kpis soc-inbox-summary">
        <KpiCard label={t('inbox.m.reports')} value={data?.reports.length ?? '—'} />
        <KpiCard label={t('inbox.m.low', { n: data?.threshold ?? '—' })} value={data?.employees.length ?? '—'} />
      </div>
      {error && <p className="field-error" role="alert">{t('inbox.err.refresh')}</p>}
      <div className="ops-toolbar">
        <div className="seg" role="group" aria-label={t('inbox.tabs')} style={{ flexWrap: 'wrap' }}>
          {tabs.map(({ id, label, icon: Icon }) => <button key={id} type="button" aria-pressed={tab === id} onClick={() => setTab(id)}><Icon size={14} aria-hidden="true" />{label}</button>)}
        </div>
        <button type="button" className="btn" onClick={refresh} disabled={isLoading}><RefreshCw size={14} aria-hidden="true" /> {t('inbox.refresh')}</button>
      </div>

      {isLoading && !data && tab !== 'access' && <StateMessage variant="loading" title={t('inbox.loading')} />}

      {tab === 'reports' && data && <div className="ops-block">
        <div className="ops-head"><p className="emp-muted">{t('inbox.reports.help')}</p>{onOpenIncidents && <button className="btn" onClick={onOpenIncidents}>{t('soc.inbox.open')}</button>}</div>
        <DataTable<Report> caption={t('inbox.tab.reports')} rows={data.reports} rowKey={r => r.id} pageSize={10} density="comfortable" onRowClick={setViewingReport} columns={[
          { key: 'url', header: t('threat.col.indicator'), render: r => <span className="cell-clip" title={r.url}>{r.url}</span> },
          { key: 'person', header: t('login.col.person'), secondary: true, render: r => <span className="cell-clip" title={r.email}>{r.email}</span> },
          { key: 'status', header: t('soc.record.status'), render: r => <StatusChip tone={['resolved','false positive'].includes(r.status) ? 'ok' : 'open'}>{status(r.status)}</StatusChip> },
          { key: 'time', header: t('soc.recorded'), secondary: true, render: r => formatAgo(r.created_at, lang, now) },
        ]} empty={<StateMessage variant="empty" title={t('inbox.reports.empty')} why=" " />} />
      </div>}

      {tab === 'access' && <AccessRequestsPanel canDecide={canDecideAccess} />}

      {tab === 'employees' && data && <div className="ops-block">
        <p className="emp-muted">{t('inbox.emp.help', { n: data.threshold })}</p>
        <DataTable<Employee> caption={t('inbox.tab.warnings')} rows={data.employees} rowKey={e => String(e.id)} pageSize={10} density="comfortable" columns={[
          { key: 'employee', header: t('login.col.person'), render: e => <span className="cell-clip" title={e.email}>{e.email}<small className="cell-sub">{e.divisi}</small></span> },
          { key: 'points', header: t('soc.points'), render: e => `${e.points}/200` },
          { key: 'delivery', header: t('soc.record.status'), render: e => delivery(e) },
          { key: 'send', header: t('threat.col.remediation'), render: employee => <button type="button" className="btn" disabled={!employee.canSend || !data.emailEnabled} onClick={() => { setSelected(employee); setSendError(''); }}><Mail size={14} aria-hidden="true" />{employee.canSend ? t('inbox.emp.send') : t('inbox.emp.cooldown')}</button> },
        ]} empty={<StateMessage variant="empty" title={t('inbox.emp.empty')} why=" " />} />
      </div>}

      {tab === 'audit' && data && <div className="ops-block">
        <DataTable<Audit> caption={t('inbox.tab.audit')} rows={data.audit} rowKey={a => String(a.id)} pageSize={10} density="comfortable" columns={[
          { key: 'recipient', header: t('login.col.person'), render: a => <span className="cell-clip" title={a.recipient}>{a.recipient}</span> },
          { key: 'actor', header: t('aud.col.who'), secondary: true, render: a => <span className="cell-clip">{a.actor_email}</span> },
          { key: 'reason', header: t('aud.col.reason'), render: a => <span className="cell-preview" title={a.reason}>{a.reason}</span> },
          { key: 'at', header: t('soc.recorded'), secondary: true, render: a => formatAgo(a.created_at, lang, now) },
        ]} empty={<StateMessage variant="empty" title={t('inbox.audit.empty')} why=" " />} />
      </div>}

      <Dialog open={viewingReport !== null} onClose={() => setViewingReport(null)} title={t('soc.source.employee')} size="md">
        {viewingReport && <div className="audit-detail"><dl><div><dt>{t('threat.col.indicator')}</dt><dd>{viewingReport.url}</dd></div><div><dt>{t('login.col.person')}</dt><dd>{viewingReport.email}</dd></div><div><dt>{t('soc.record.status')}</dt><dd>{status(viewingReport.status)}</dd></div><div><dt>{t('aud.col.reason')}</dt><dd>{viewingReport.description || t('inbox.reports.nodesc')}</dd></div></dl><ThreatEvidence analysis={viewingReport.analysis} /></div>}
      </Dialog>
      <Dialog open={selected !== null} onClose={() => setSelected(null)} busy={busy} title={t('inbox.dialog.title')} description={selected ? t('inbox.dialog.person', { email: selected.email, points: selected.points }) : undefined}
        footer={<>
          <button type="button" className="btn" disabled={busy} onClick={() => setSelected(null)}>{t('common.cancel')}</button>
          <button type="submit" form="warning-form" className="btn btn-primary" disabled={busy}>{busy ? t('inbox.dialog.submitting') : t('inbox.dialog.submit')}</button>
        </>}>
        <form id="warning-form" className="ui-form" onSubmit={send}>
          <Field label={t('inbox.dialog.reason')} hint={t('inbox.dialog.note')} error={sendError}>{c => <textarea {...c} required minLength={5} maxLength={1000} rows={4} value={reason} onChange={event => setReason(event.target.value)} />}</Field>
        </form>
      </Dialog>
    </section>
  );
}
