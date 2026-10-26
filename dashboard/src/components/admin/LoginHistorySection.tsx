'use client';

import { RefreshCw } from 'lucide-react';
import { AdminLoginEvent } from '@/components/admin/types';
import DataTable, { type Column } from '@/components/ui/DataTable';
import StatusChip from '@/components/ui/StatusChip';
import StateMessage from '@/components/ui/StateMessage';
import LoadGate from '@/components/ui/LoadGate';
import type { LoadState } from '@/lib/loadState';
import { useI18n } from '@/i18n/I18nProvider';
import { parseUtcDate } from '@/components/admin/types';
import type { MessageKey } from '@/i18n/messages';

interface LoginHistorySectionProps {
  readOnly: boolean;
  loginHistory: AdminLoginEvent[] | { logs?: AdminLoginEvent[]; loginHistory?: AdminLoginEvent[] };
  state?: LoadState;
}

export default function LoginHistorySection({ loginHistory, state }: LoginHistorySectionProps) {
  const { t, lang } = useI18n();
  const logs = Array.isArray(loginHistory) ? loginHistory : loginHistory?.logs || loginHistory?.loginHistory || [];

  const columns: Column<AdminLoginEvent>[] = [
    { key: 'email', header: t('login.col.person'), render: log => <span className="cell-clip" title={log.reason}>{log.email}</span> },
    { key: 'role', header: t('soc.auth.role'), secondary: true, render: log => ['employee','soc','phishing_admin'].includes(log.role || '') ? t(`role.${log.role}` as MessageKey) : '—' },
    { key: 'event', header: t('soc.auth.event'), render: log => ['password_failed','otp_requested','otp_resent','otp_verified','otp_failed','logout'].includes(log.event_type || '') ? t(`soc.auth.${log.event_type}` as MessageKey) : log.event_type?.replaceAll('_', ' ') || t('soc.auth.unknown') },
    { key: 'time', header: t('login.col.time'), sortValue: log => log.login_time, render: log => <time dateTime={parseUtcDate(log.login_time).toISOString()} title={parseUtcDate(log.login_time).toLocaleString()}>{parseUtcDate(log.login_time).toLocaleString(lang === 'id' ? 'id-ID' : 'en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</time> },
    { key: 'result', header: t('soc.auth.result'), render: log => log.success == null ? '—' : <StatusChip tone={log.success ? 'ok' : 'warn'}>{t(log.success ? 'soc.auth.success' : 'soc.auth.failed')}</StatusChip> },
  ];

  return (
    <section className="ops-block" aria-labelledby="login-history-title">
      <div className="ops-head">
        <div><h3 id="login-history-title" className="visually-hidden">{t('login.title')}</h3><p className="emp-muted">{t('soc.auth.note')}</p></div>
        <div className="ops-actions"><span className="emp-muted">{t('login.count', { n: logs.length })}</span>{state?.retry && <button className="btn" onClick={state.retry}><RefreshCw size={14} />{t('common.refresh')}</button>}</div>
      </div>
      <LoadGate state={state} errorTitle="err.logins">
      <DataTable
        caption={t('login.title')}
        columns={columns}
        rows={logs}
        rowKey={log => String(log.id)}
        pageSize={10}
        density="comfortable"
        empty={<StateMessage variant="empty" title={t('login.empty.title')} why={t('login.empty.why')} />}
      />
      </LoadGate>
    </section>
  );
}
