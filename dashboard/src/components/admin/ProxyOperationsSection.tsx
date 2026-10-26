'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Ban, CheckCircle2 } from 'lucide-react';
import Dialog from '@/components/ui/Dialog';
import SeverityBadge from '@/components/ui/SeverityBadge';
import StateMessage from '@/components/ui/StateMessage';
import LoadGate from '@/components/ui/LoadGate';
import { useScrollCue } from '@/hooks/useScrollCue';
import { loadState } from '@/lib/loadState';
import StatusChip from '@/components/ui/StatusChip';
import { useToast } from '@/components/ui/Toast';
import { useI18n } from '@/i18n/I18nProvider';
import { serverMessage } from '@/lib/serverError';
import { useNow } from '@/hooks/useNow';
import { formatAgo } from '@/lib/relativeTime';

type Alert = {
  id: string;
  domain: string;
  employee_email?: string;
  urgency: 'Critical' | 'Unknown';
  status: 'open' | 'blocked' | 'allowed';
  verdict: 'malicious' | 'unknown';
  reason: string;
  confidence?: number | null;
  source: string;
  created_at: string;
  stalePrediction?: boolean;
};

type Verdict = {
  id: string;
  domain: string;
  source: 'soc' | 'ml' | 'employee_report';
  decision: 'allow' | 'block';
  reason: string;
  confidence?: number | null;
  model_version?: string | null;
  updated_at: string;
};

type Traffic = {
  event_id: string;
  domain: string;
  employee_email?: string | null;
  method: string;
  port?: number | null;
  action: 'allow' | 'block';
  decision_source: string;
  reason: string;
  occurred_at: string;
};

const TRAFFIC_ROWS = 50;
const TRAFFIC_STEP = 10;
const ALERT_ROWS = 5;

interface ProxyOperationsSectionProps {
  /** Which part of the page is showing. 'other' hides both parts here and lets `children` (the other tabs) show. */
  view?: 'live' | 'policies' | 'other';
  /** The tab row; it sits between the summary strip and the panels. */
  tabs?: ReactNode;
  /** Reports how many alerts are open, for the tab badge. */
  onOpenAlerts?: (count: number) => void;
  children?: ReactNode;
}

export default function ProxyOperationsSection({ view = 'live', tabs, onOpenAlerts, children }: ProxyOperationsSectionProps = {}) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const now = useNow();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [traffic, setTraffic] = useState<Traffic[]>([]);
  const [trafficSnapshot, setTrafficSnapshot] = useState<Traffic[] | null>(null);
  const displayedTraffic = trafficSnapshot ?? traffic;
  const [streamOnline, setStreamOnline] = useState(false);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [trafficRows, setTrafficRows] = useState(TRAFFIC_STEP);
  const [loaded, setLoaded] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [domain, setDomain] = useState('');
  const [action, setAction] = useState<'block' | 'allow'>('block');
  const [reason, setReason] = useState('');
  const [policyError, setPolicyError] = useState('');
  const [queueFilter, setQueueFilter] = useState('actionable');
  const [review, setReview] = useState<
    { kind: 'alert'; item: Alert; action: 'block' | 'allow' } |
    { kind: 'traffic'; item: Traffic; action: 'block' } | null
  >(null);
  const [reviewReason, setReviewReason] = useState('');
  const [reviewError, setReviewError] = useState('');

  const load = useCallback(async () => {
    try {
      const [alertResponse, verdictResponse, trafficResponse] = await Promise.all([
        fetch('/api/proxy/alerts', { cache: 'no-store' }),
        fetch('/api/proxy/verdicts', { cache: 'no-store' }),
        fetch('/api/proxy/traffic?limit=200', { cache: 'no-store' }),
      ]);
      if (alertResponse.ok) setAlerts((await alertResponse.json()).alerts || []);
      if (verdictResponse.ok) setVerdicts((await verdictResponse.json()).verdicts || []);
      if (trafficResponse.ok) setTraffic((await trafficResponse.json()).events || []);
      const allOk = alertResponse.ok && verdictResponse.ok && trafficResponse.ok;
      if (alertResponse.ok || trafficResponse.ok) setLoaded(true);
      setLoadFailed(!allOk);
      setMessage(allOk ? '' : t('ops.fail.refresh'));
    } catch { setLoadFailed(true); setMessage(t('ops.fail.refresh')); }
  }, [t]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    const stream = new EventSource('/api/proxy/alerts/stream');
    stream.addEventListener('ready', () => setStreamOnline(true));
    stream.addEventListener('update', (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data);
        if (payload.type === 'traffic.observed' && payload.traffic) {
          setTraffic((current) => [
            payload.traffic,
            ...current.filter((item) => item.event_id !== payload.traffic.event_id),
          ].slice(0, 200));
          return;
        }
      } catch {
        // Non-traffic events fall through to an authoritative refresh.
      }
      void load();
    });
    stream.onerror = () => setStreamOnline(false);
    return () => stream.close();
  }, [load]);

  const feedState = loadState(!loaded && !loadFailed, loadFailed, loaded, () => void load());

  // The reason starts empty on purpose: a pre-filled "Blocked by SOC" would satisfy the rule without saying anything.
  const openReview = (next: NonNullable<typeof review>, startingReason = '') => {
    setReview(next); setReviewReason(startingReason); setReviewError('');
  };

  const decideAlert = async (alert: Alert, nextAction: 'block' | 'allow', decisionReason: string) => {
    setBusy(alert.id);
    try {
      const response = await fetch(`/api/proxy/alerts/${alert.id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: nextAction, reason: decisionReason }),
      });
      const payload = await response.json();
      if (response.ok) { toast.show({ message: t('ops.toast.policy', { domain: alert.domain }), tone: 'ok' }); await load(); }
      else setReviewError(serverMessage(payload, t, 'ops.fail.save'));
      return response.ok;
    } catch {
      setReviewError(t('ops.fail.unconfirmed'));
      return false;
    }
    finally { setBusy(''); }
  };

  const submitManual = async (event: FormEvent) => {
    event.preventDefault();
    if (reason.trim().length < 5) { setPolicyError(t('ops.dialog.short')); return; }
    setPolicyError('');
    setBusy('manual');
    try {
      const response = await fetch('/api/proxy/manual-decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, action, reason }),
      });
      const payload = await response.json();
      if (response.ok) {
        toast.show({ message: t('ops.toast.applied', { action: t(action === 'block' ? 'ops.action.block' : 'ops.action.allow'), domain: payload.verdict?.domain || domain }), tone: 'ok' });
        setDomain(''); setReason(''); await load();
      } else setPolicyError(serverMessage(payload, t, 'ops.fail.policy'));
    } catch { setPolicyError(t('ops.fail.policy')); }
    finally { setBusy(''); }
  };

  const blockTraffic = async (item: Traffic, decisionReason: string) => {
    setBusy(item.event_id);
    try {
      const response = await fetch('/api/proxy/manual-decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: item.domain, action: 'block', reason: decisionReason }),
      });
      const payload = await response.json();
      if (response.ok) { toast.show({ message: t('ops.toast.blocked', { domain: payload.verdict?.domain || item.domain }), tone: 'ok' }); await load(); }
      else setReviewError(serverMessage(payload, t, 'ops.fail.save'));
      return response.ok;
    } catch {
      setReviewError(t('ops.fail.unconfirmed'));
      return false;
    }
    finally { setBusy(''); }
  };

  const counts = useMemo(() => ({
    open: alerts.filter((item) => item.status === 'open' && !item.stalePrediction && (item.urgency === 'Critical' || item.source === 'employee_report')).length,
    blocked: verdicts.filter((item) => item.source === 'soc' && item.decision === 'block').length,
    traffic: traffic.length,
  }), [alerts, traffic, verdicts]);
  useEffect(() => { onOpenAlerts?.(counts.open); }, [counts.open, onOpenAlerts]);
  const [alertsWrap, alertsMore] = useScrollCue(`${view}:${loaded}:${alerts.length}:${showAllAlerts}`);
  const [trafficWrap, trafficMore] = useScrollCue(`${view}:${loaded}:${traffic.length}:${trafficRows}`);
  const visibleAlerts = alerts.filter(item => queueFilter === 'all' || (queueFilter === 'history' ? item.status !== 'open' || item.stalePrediction : item.status === 'open' && !item.stalePrediction && (queueFilter === 'unknown' ? item.urgency === 'Unknown' && item.source !== 'employee_report' : item.urgency === 'Critical' || item.source === 'employee_report')));
  const ago = (value: string) => formatAgo(value, lang, now);
  // Derived from the traffic window already loaded (latest 200 events), so no extra request.
  const topBlocked = useMemo(() => {
    const byDomain = new Map<string, { domain: string; count: number; last: string }>();
    for (const item of traffic) {
      if (item.action !== 'block') continue;
      const entry = byDomain.get(item.domain) || { domain: item.domain, count: 0, last: item.occurred_at };
      entry.count += 1;
      if (item.occurred_at > entry.last) entry.last = item.occurred_at;
      byDomain.set(item.domain, entry);
    }
    return [...byDomain.values()].sort((a, b) => b.count - a.count || (a.last < b.last ? 1 : -1)).slice(0, 5);
  }, [traffic]);
  const lastTraffic = traffic.reduce<string | null>((latest, item) => (!latest || item.occurred_at > latest ? item.occurred_at : latest), null);
  const blocking = review?.action === 'block';

  const submitReview = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !review) return;
    const trimmedReason = reviewReason.trim();
    if (trimmedReason.length < 5) { setReviewError(t('ops.dialog.short')); return; }
    setReviewError('');
    const saved = review.kind === 'alert'
      ? await decideAlert(review.item, review.action, trimmedReason)
      : await blockTraffic(review.item, trimmedReason);
    if (saved) setReview(null);
  };

  return (
    <section className="proxy-ops ops-page">
      <div className="ops-intro">
        <p className="debt-help">{t('ops.desc')}</p>
        <span className="ops-gateway">
          <span className="emp-muted">{lastTraffic ? t('ops.gateway.last', { when: ago(lastTraffic) }) : t('ops.gateway.none')}</span>
          <StatusChip tone={streamOnline && !loadFailed ? 'ok' : 'warn'}>{t(loadFailed ? 'soc.updates.delayed' : streamOnline ? 'ops.stream.on' : 'ops.stream.off')}</StatusChip>
          <button type="button" className="btn" onClick={() => void load()}>{t('common.refresh')}</button>
        </span>
      </div>
      <div className="strip" aria-label={t('ops.desc')}>
        <span className="strip-static"><b>{counts.open}</b>{t('ops.stat.alerts')}</span>
        <span className="strip-static"><b>{counts.blocked}</b>{t('ops.stat.blocks')}</span>
        <span className="strip-static"><b>{counts.traffic}</b>{t('ops.stat.traffic')}</span>
      </div>
      {message && <p className={message === t('ops.fail.refresh') ? 'soc-update-note' : 'debt-error'} role={message === t('ops.fail.refresh') ? 'status' : 'alert'}>{message}</p>}
      {tabs}

      <div role="tabpanel" id="traffic-panel-live" aria-labelledby="traffic-tab-live" hidden={view !== 'live'} className="ops-main">
          <section className="ops-block" aria-labelledby="ops-alerts">
            <div className="ops-head"><h3 id="ops-alerts">{t('ops.alerts.title')}</h3><span className="emp-muted">{t('ops.alerts.count', { n: counts.open })}</span></div>
            <label className="ops-filter">{t('ops.filter.show')}
              <select value={queueFilter} onChange={event => setQueueFilter(event.target.value)}>
                <option value="actionable">{t('ops.filter.actionable')}</option>
                <option value="unknown">{t('ops.filter.unknown')}</option>
                <option value="history">{t('ops.filter.history')}</option>
                <option value="all">{t('ops.filter.all')}</option>
              </select>
            </label>
            <p className="debt-help">{t('ops.alerts.help')}</p>
            <LoadGate state={feedState} errorTitle="err.alerts" compact>
            {visibleAlerts.length === 0
              ? <StateMessage variant="empty" title={t('ops.alerts.empty')} compact />
              : <div ref={alertsWrap} className="table-wrap" data-more={alertsMore || undefined} role="region" aria-label={t('ops.alerts.caption')} tabIndex={0}><table className="data-table">
                  <caption className="visually-hidden">{t('ops.alerts.caption')}</caption>
                  <thead><tr><th scope="col">{t('ops.col.urgency')}</th><th scope="col">{t('ops.col.domain')}</th><th scope="col" data-secondary>{t('ops.col.reason')}</th><th scope="col" data-secondary>{t('ops.col.client')}</th><th scope="col" data-narrow-hide>{t('ops.col.time')}</th><th scope="col">{t('ops.col.action')}</th></tr></thead>
                  <tbody>
                    {visibleAlerts.slice(0, showAllAlerts ? undefined : ALERT_ROWS).map((alert) => (
                      <tr key={alert.id}>
                        <td>{alert.stalePrediction
                          ? <SeverityBadge level="info" label={t('ops.urgency.historical')} />
                          : alert.urgency === 'Critical' ? <SeverityBadge level="critical" label={t('ops.urgency.critical')} /> : <SeverityBadge level="info" label={t('ops.urgency.unknown')} />}</td>
                        <td><span className="mono">{alert.domain}</span></td>
                        <td data-secondary><span className="cell-clip" title={alert.reason}>{alert.reason}</span></td>
                        <td data-secondary>{alert.employee_email || 'ML'}<small className="cell-sub">{alert.source.toUpperCase()}{alert.confidence != null ? ` · ${Math.round(alert.confidence * 100)}%` : ''}</small></td>
                        <td data-narrow-hide title={new Date(alert.created_at).toLocaleString()}>{ago(alert.created_at)}</td>
                        <td>{alert.status === 'open'
                          ? <span className="ops-actions">
                              <button type="button" className="btn" disabled={!!busy} onClick={() => openReview({ kind: 'alert', item: alert, action: 'allow' }, '')}><CheckCircle2 size={14} aria-hidden="true" />{t('ops.action.allow')}</button>
                              <button type="button" className="btn btn-danger" disabled={!!busy} onClick={() => openReview({ kind: 'alert', item: alert, action: 'block' }, '')}><Ban size={14} aria-hidden="true" />{t('ops.action.block')}</button>
                            </span>
                          : <StatusChip tone={alert.status === 'blocked' ? 'bad' : 'ok'}>{t(alert.status === 'blocked' ? 'ops.status.blocked' : 'ops.status.allowed')}</StatusChip>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>}
            {visibleAlerts.length > ALERT_ROWS && <div className="ops-more"><button type="button" className="btn" aria-expanded={showAllAlerts} onClick={() => setShowAllAlerts(value => !value)}>{showAllAlerts ? t('ops.showFewer') : t('ops.showAll', { n: visibleAlerts.length })}</button></div>}
            </LoadGate>
          </section>

          <section className="ops-block" aria-labelledby="ops-traffic">
            <div className="ops-head"><h3 id="ops-traffic">{t('ops.traffic.title')}</h3><div className="ops-actions"><span className="emp-muted">{t('ops.traffic.count', { n: displayedTraffic.length })}</span><button type="button" className="btn" aria-pressed={trafficSnapshot !== null} onClick={() => setTrafficSnapshot(trafficSnapshot ? null : [...traffic])}>{t(trafficSnapshot ? 'soc.feed.resume' : 'soc.feed.pause')}</button></div></div>
            {trafficSnapshot && <p className="soc-update-note" role="status">{t('soc.feed.paused')}</p>}
            <LoadGate state={feedState} errorTitle="err.alerts" compact>
            {displayedTraffic.length === 0
              ? <StateMessage variant="empty" title={t('ops.traffic.empty')} compact />
              : <div ref={trafficWrap} className="table-wrap" data-more={trafficMore || undefined} role="region" aria-label={t('ops.traffic.caption')} tabIndex={0}><table className="data-table">
                  <caption className="visually-hidden">{t('ops.traffic.caption')}</caption>
                  <thead><tr><th scope="col" data-narrow-hide>{t('ops.col.time')}</th><th scope="col">{t('ops.col.domain')}</th><th scope="col" data-secondary>{t('ops.col.client')}</th><th scope="col">{t('ops.col.decision')}</th><th scope="col" data-secondary>{t('ops.col.source')}</th><th scope="col">{t('ops.col.action')}</th></tr></thead>
                  <tbody>
                    {displayedTraffic.slice(0, trafficRows).map((item) => (
                      <tr key={item.event_id}>
                        <td data-narrow-hide title={new Date(item.occurred_at).toLocaleString()}>{ago(item.occurred_at)}</td>
                        <td><span className="mono">{item.domain}{item.port ? `:${item.port}` : ''}</span></td>
                        <td data-secondary>{item.employee_email || t('ops.traffic.unidentified')}</td>
                        <td>{item.action === 'block'
                          ? <StatusChip tone="bad">{t('ops.status.blocked')}</StatusChip>
                          : ['soc', 'ml'].includes(item.decision_source) ? <StatusChip tone="ok">{t('ops.status.allowed')}</StatusChip> : <StatusChip tone="warn">{t('ops.traffic.unknownAllowed')}</StatusChip>}</td>
                        <td data-secondary><span className="cell-clip" title={item.reason}>{item.method} · {item.decision_source.toUpperCase()}</span></td>
                        <td>{item.action !== 'block' && <button type="button" className="btn btn-danger" disabled={!!busy} onClick={() => openReview({ kind: 'traffic', item, action: 'block' }, '')}><Ban size={14} aria-hidden="true" />{t('ops.action.block')}</button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>}
            </LoadGate>
            {displayedTraffic.length > trafficRows && <div className="ops-more"><button type="button" className="btn" onClick={() => setTrafficRows(rows => Math.min(TRAFFIC_ROWS, rows + TRAFFIC_STEP))}>{t('ops.showMore')}</button></div>}
            {displayedTraffic.length > TRAFFIC_ROWS && trafficRows >= TRAFFIC_ROWS && <p className="emp-muted">{t('ops.traffic.more', { n: TRAFFIC_ROWS })}</p>}
          </section>
          <details className="ops-fold">
            <summary>{t('ops.blocked.title')}<span className="emp-muted">{topBlocked.length}</span></summary>
          <div className="ops-card">
            {topBlocked.length === 0 && <p className="emp-muted">{t('ops.blocked.empty')}</p>}
            <ul className="emp-list">
              {topBlocked.map((item) => (
                <li key={item.domain}>
                  <span className="emp-list-main"><span className="mono">{item.domain}</span><small>{t('ops.blocked.last', { when: ago(item.last) })}</small></span>
                  <StatusChip tone="bad">{t('ops.blocked.count', { n: item.count })}</StatusChip>
                </li>
              ))}
            </ul>
          </div>
          </details>
      </div>

      <div role="tabpanel" id="traffic-panel-policies" aria-labelledby="traffic-tab-policies" hidden={view !== 'policies'} className="ops-policies">
          <form className="ops-card" onSubmit={submitManual} noValidate>
            <h3>{t('ops.policy.title')}</h3>
            <div className="field"><label htmlFor="policy-domain">{t('ops.policy.domain')}</label><input id="policy-domain" required value={domain} onChange={(event) => setDomain(event.target.value)} placeholder={t('ops.policy.placeholder')} /><small>{t('ops.policy.hint')}</small></div>
            <div className="field"><label htmlFor="policy-action">{t('ops.policy.decision')}</label><select id="policy-action" value={action} onChange={(event) => setAction(event.target.value as 'block' | 'allow')}><option value="block">{t('ops.action.block')}</option><option value="allow">{t('ops.action.allow')}</option></select></div>
            <div className="field" data-invalid={Boolean(policyError)}><label htmlFor="policy-reason">{t('ops.policy.reason')}</label><textarea id="policy-reason" required minLength={5} value={reason} onChange={(event) => setReason(event.target.value)} placeholder={t('ops.policy.reason.placeholder')} />{policyError && <small className="field-error" role="alert">{policyError}</small>}</div>
            <button type="submit" className="btn btn-primary" disabled={busy === 'manual'}>{busy === 'manual' ? t('ops.policy.saving') : t('ops.policy.apply')}</button>
          </form>
          <div className="ops-card">
            <h3>{t('ops.recent.title')}</h3>
            {verdicts.length === 0 && <p className="emp-muted">{t('ops.recent.empty')}</p>}
            <ul className="emp-list">
              {verdicts.slice(0, 8).map((item) => (
                <li key={item.id}>
                  <span className="emp-list-main"><span className="mono">{item.domain}</span><small>{item.source === 'soc' ? t('ops.recent.manual') : t('ops.recent.model', { v: item.model_version || '' })}</small></span>
                  <StatusChip tone={item.decision === 'block' ? 'bad' : 'ok'}>{t(item.decision === 'block' ? 'ops.status.blocked' : 'ops.status.allowed')}</StatusChip>
                </li>
              ))}
            </ul>
          </div>
      </div>

      {children}

      <Dialog open={review !== null} onClose={() => { if (!busy) setReview(null); }} busy={!!busy} size="md" title={blocking ? t('ops.dialog.block') : t('ops.dialog.allow')}>
        {review && <>
          <p className="decision-domain mono">{review.item.domain}</p>
          {review.item.reason && <p className="decision-reason-text">{review.item.reason}</p>}
          <form className="ui-form" onSubmit={submitReview}>
            <div className="field" data-invalid={Boolean(reviewError)}>
              <label htmlFor="decision-reason">{t('ops.dialog.reason')}</label>
              <textarea id="decision-reason" placeholder={t('ops.dialog.placeholder')} autoFocus required minLength={5} maxLength={1000} rows={3} value={reviewReason} onChange={event => setReviewReason(event.target.value)} />
              <small>{t('ops.dialog.hint')}</small>
              {reviewError && <small className="field-error" role="alert">{reviewError}</small>}
            </div>
            <div className="ui-dialog-footer">
              <button type="button" className="btn" disabled={!!busy} onClick={() => setReview(null)}>{t('common.cancel')}</button>
              <button type="submit" className={`btn ${blocking ? 'btn-danger' : 'btn-primary'}`} disabled={!!busy}>{busy ? t('ops.dialog.saving') : blocking ? t('ops.dialog.confirmBlock') : t('ops.dialog.confirmAllow')}</button>
            </div>
          </form>
        </>}
      </Dialog>
    </section>
  );
}
