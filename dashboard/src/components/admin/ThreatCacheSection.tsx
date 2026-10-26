'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { Plus } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ThreatCacheEntry } from '@/components/admin/types';
import DataTable, { type Column } from '@/components/ui/DataTable';
import Dialog from '@/components/ui/Dialog';
import Field from '@/components/ui/Field';
import FilterBar from '@/components/ui/FilterBar';
import StateMessage from '@/components/ui/StateMessage';
import LoadGate from '@/components/ui/LoadGate';
import type { LoadState } from '@/lib/loadState';
import StatusChip, { type StatusTone } from '@/components/ui/StatusChip';
import { useToast } from '@/components/ui/Toast';
import { useI18n } from '@/i18n/I18nProvider';
import { serverMessage } from '@/lib/serverError';
import { useNow } from '@/hooks/useNow';
import { formatAgo } from '@/lib/relativeTime';
import type { MessageKey } from '@/i18n/messages';

interface ThreatCacheSectionProps {
  readOnly: boolean;
  cacheData: ThreatCacheEntry[];
  state?: LoadState;
  threatTypeFilter: string;
  threatActionFilter: string;
  onThreatTypeFilterChange: (val: string) => void;
  onThreatActionFilterChange: (val: string) => void;
}

const TYPES = ['PHISHING_CLICK', 'PHISHING_REPORT', 'MALWARE_DETECTED', 'SUSPICIOUS_URL', 'DLP_VIOLATION'];
const ACTIONS = ['block', 'allow', 'warning'];
const ACTION_TONE: Record<string, StatusTone> = { block: 'bad', warning: 'warn', allow: 'ok', notify_soc: 'open' };

type Action = 'block' | 'allow' | 'purge';

export default function ThreatCacheSection({ readOnly, state, cacheData, threatTypeFilter, threatActionFilter, onThreatTypeFilterChange, onThreatActionFilterChange }: ThreatCacheSectionProps) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const now = useNow();
  const [adding, setAdding] = useState(false);
  const [indicator, setIndicator] = useState('');
  const [action, setAction] = useState<'block' | 'allow'>('block');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [formError, setFormError] = useState('');
  const [reviewing, setReviewing] = useState<ThreatCacheEntry | null>(null);
  const review = (entry: ThreatCacheEntry) => {
    setReviewing(entry); setIndicator(entry.url); setAction(entry.action === 'block' ? 'allow' : 'block');
    setReason(''); setFormError(''); setAdding(true);
  };

  const execute = async (target: string, kind: Action, why?: string): Promise<boolean> => {
    setBusy(`${kind}-${target}`);
    try {
      const res = await fetch('/api/admin/threats/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ indicator: target, action: kind, reason: why }) });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success) { toast.show({ message: t('threat.ok', { action: t(`threat.btn.${kind}` as MessageKey) }), tone: 'ok' }); return true; }
      const message = serverMessage(data, t, 'threat.err.generic');
      if (adding) setFormError(message); else toast.show({ message, tone: 'bad' });
    } catch {
      if (adding) setFormError(t('threat.err.network')); else toast.show({ message: t('threat.err.network'), tone: 'bad' });
    } finally {
      setBusy(null);
    }
    return false;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError('');
    if (!indicator.trim()) return;
    if (!await execute(indicator.trim(), action, reason.trim())) return;
    setIndicator(''); setReason(''); setAdding(false);
  };

  const filtered = useMemo(() => cacheData.filter(entry =>
    (threatTypeFilter === 'ALL' || entry.threatType?.toUpperCase().includes(threatTypeFilter.toUpperCase())) &&
    (threatActionFilter === 'ALL' || entry.action?.toUpperCase() === threatActionFilter.toUpperCase())), [cacheData, threatTypeFilter, threatActionFilter]);

  const chartData = useMemo(() => Object.values(cacheData.reduce<Record<string, { date: string; detections: number }>>((acc, item) => {
    const date = item.detectedAt ? new Date(item.detectedAt).toLocaleDateString(lang === 'id' ? 'id-ID' : 'en-US', { month: 'short', day: 'numeric' }) : t('threat.chart.today');
    acc[date] = acc[date] || { date, detections: 0 };
    acc[date].detections += 1;
    return acc;
  }, {})).reverse(), [cacheData, lang, t]);

  const actionLabel = (value?: string) => {
    const key = `threat.action.${(value || 'unknown').toLowerCase()}` as MessageKey;
    if (value === 'warning' || value === 'notify_soc') return t('soc.record.review');
    return ['block', 'allow'].includes((value || '').toLowerCase()) ? t(key) : t('threat.action.unknown');
  };

  const columns: Column<ThreatCacheEntry>[] = [
    { key: 'url', header: t('threat.col.indicator'), render: e => <span className="cell-clip" title={e.url}>{e.url || '—'}</span> },
    { key: 'source', header: t('threat.col.source'), secondary: true, render: e => <span className="cell-clip" title={e.source}>{e.source.startsWith('User Report') ? t('soc.source.employee') : e.source.replaceAll('virustotal', 'VirusTotal').replaceAll(',', ' · ')}</span> },
    { key: 'action', header: t('soc.record.status'), render: e => <StatusChip tone={e.action === 'allow' && e.source !== 'SOC Whitelist' ? 'neutral' : ACTION_TONE[(e.action || '').toLowerCase()] ?? 'neutral'}>{e.action === 'allow' && e.source !== 'SOC Whitelist' ? t('soc.record.noAlert') : actionLabel(e.action)}</StatusChip> },
    { key: 'detected', header: t('soc.recorded'), secondary: true, sortValue: e => e.detectedAt, render: e => formatAgo(e.detectedAt, lang, now) },
    ...(readOnly ? [] : [{
      key: 'do', header: t('threat.col.remediation'), align: 'right' as const, render: (e: ThreatCacheEntry) => (
        <span className="ops-actions">
          <button type="button" className="btn" disabled={busy !== null} onClick={() => review(e)}>{t('soc.review')}</button>
        </span>
      ),
    }]),
  ];

  const typeOptions = [{ value: 'ALL', label: t('threat.type.all') }, ...[...new Set(cacheData.map(item => item.threatType).filter(Boolean))].sort().map(value => ({ value, label: TYPES.includes(value) ? t(`threat.type.${value}` as MessageKey) : value.replaceAll('_', ' ') }))];
  const actionOptions = [{ value: 'ALL', label: t('threat.action.all') }, ...ACTIONS.map(v => ({ value: v.toUpperCase(), label: v === 'warning' ? t('soc.record.review') : t(`threat.action.${v}` as MessageKey) }))];

  return (
    <div className="ops-page">
      <details className="soc-trend"><summary>{t('soc.activity.trend')}</summary><p className="emp-muted">{t('soc.activity.note')}</p>
      <section className="ops-block" aria-labelledby="threat-chart-title">
        <div className="ops-head"><h3 id="threat-chart-title">{t('threat.chart.title')}</h3></div>
        <LoadGate state={state} errorTitle="err.threats" lines={3}>
        <div className="ops-card" style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip cursor={false} itemStyle={{ color: 'var(--text-primary)' }} labelStyle={{ color: 'var(--text-secondary)' }} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} formatter={value => [value, t('threat.chart.series')]} />
              <Bar dataKey="detections" fill="var(--accent)" radius={[4, 4, 0, 0]} barSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        </LoadGate>
      </section>
      </details>

      <section className="ops-block" aria-labelledby="threat-feed-title">
        <div className="ops-head">
          <h3 id="threat-feed-title">{t('threat.title')}</h3>
          <div className="ops-actions"><span className="emp-muted">{t('threat.count', { shown: filtered.length, total: cacheData.length })}</span>{!readOnly && <button type="button" className="btn btn-primary" onClick={() => { setReviewing(null); setIndicator(''); setReason(''); setAction('block'); setFormError(''); setAdding(true); }}><Plus size={14} aria-hidden="true" />{t('threat.add')}</button>}</div>
        </div>
        <FilterBar
          selects={[
            { id: 'type', label: t('threat.filter.type'), value: threatTypeFilter, options: typeOptions, onChange: onThreatTypeFilterChange },
            { id: 'action', label: t('threat.filter.action'), value: threatActionFilter, options: actionOptions, onChange: onThreatActionFilterChange },
          ]}
          activeCount={(threatTypeFilter !== 'ALL' ? 1 : 0) + (threatActionFilter !== 'ALL' ? 1 : 0)}
          onClear={() => { onThreatTypeFilterChange('ALL'); onThreatActionFilterChange('ALL'); }}
        />
        <LoadGate state={state} errorTitle="err.threats">
          <DataTable key={`${threatTypeFilter}:${threatActionFilter}`} caption={t('threat.title')} columns={columns} rows={filtered} rowKey={e => e.id} pageSize={10} density="comfortable" empty={<StateMessage variant="empty" title={t('threat.empty.title')} why={t('threat.empty.why')} />} />
        </LoadGate>
      </section>

      <Dialog open={adding && !readOnly} onClose={() => setAdding(false)} busy={busy !== null} title={t(reviewing ? 'soc.review.title' : 'threat.dialog.title')} description={t(reviewing ? 'soc.review.help' : 'threat.dialog.desc')}
        footer={<>
          <button type="button" className="btn" onClick={() => setAdding(false)} disabled={busy !== null}>{t('common.cancel')}</button>
          <button type="submit" form="threat-form" className="btn btn-primary" disabled={busy !== null}>{busy ? t('threat.submitting') : t('threat.submit')}</button>
        </>}>
        <form id="threat-form" className="ui-form" onSubmit={submit}>
          <Field label={t('threat.field.indicator')}>{c => <input {...c} required value={indicator} readOnly={Boolean(reviewing)} placeholder={t('threat.field.indicator.ph')} onChange={e => setIndicator(e.target.value)} />}</Field>
          {reviewing && <dl className="acc-facts"><div><dt>{t('threat.col.source')}</dt><dd>{reviewing.source}</dd></div><div><dt>{t('soc.evidence.score')}</dt><dd>{reviewing.id.startsWith('TR-') || reviewing.source.startsWith('SOC') || reviewing.source.startsWith('User Report') ? t('soc.evidence.none') : `${reviewing.score}/100`}</dd></div></dl>}
          <Field label={t('threat.field.action')}>{c => (
            <select {...c} value={action} onChange={e => setAction(e.target.value as 'block' | 'allow')}>
              <option value="block">{t('threat.field.action.block')}</option>
              <option value="allow">{t('threat.field.action.allow')}</option>
            </select>
          )}</Field>
          <Field label={t('threat.field.reason')} error={formError}>{c => <input {...c} required minLength={5} maxLength={1000} value={reason} placeholder={t('threat.field.reason.ph')} onChange={e => setReason(e.target.value)} />}</Field>
        </form>
        {reviewing && <details className="provider-details"><summary>{t('soc.cache.clear')}</summary><p>{t('soc.cache.note')}</p><button type="button" className="btn" disabled={busy !== null} onClick={async () => { if (await execute(reviewing.url, 'purge')) setAdding(false); }}>{t('soc.cache.clear')}</button></details>}
      </Dialog>
    </div>
  );
}
