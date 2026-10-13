'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FileSearch, Flag, LockKeyhole, ShieldBan } from 'lucide-react';
import SecurityScreen from '@/components/ui/SecurityScreen';
import Field from '@/components/ui/Field';
import '@/app/security-pages.css';
import StateMessage from '@/components/ui/StateMessage';
import { useAuth } from '@/context/AuthContext';
import { useI18n } from '@/i18n/I18nProvider';
import type { MessageKey } from '@/i18n/messages';

/** Turns whatever arrives in ?reason= into one of a few plain sentences. Raw codes are never shown. */
function reasonKey(reason: string | null): MessageKey {
  const value = (reason || '').toLowerCase();
  if (/phish|credential|lookalike|impersonat/.test(value)) return 'blocked.reason.phishing';
  if (/malware|malicious|trojan|ransom|virus/.test(value)) return 'blocked.reason.malware';
  if (/polic|categor|rule/.test(value)) return 'blocked.reason.policy';
  if (/pending|review|check|scan|unknown/.test(value)) return 'blocked.reason.pending';
  return 'blocked.reason.unknown';
}

/** Shows only the host, whether we were given "example.com" or a full address. */
function hostOf(raw: string | null): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  try { return new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(value) ? value : `https://${value}`).host || null; } catch { return null; }
}

function BlockedContent() {
  const params = useSearchParams();
  const { t } = useI18n();
  const { isAuthenticated, isLoading } = useAuth();
  const domain = hostOf(params.get('domain') || params.get('url'));
  const [formOpen, setFormOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [fieldError, setFieldError] = useState('');
  const [phase, setPhase] = useState<'idle' | 'sending' | 'sent' | 'duplicate' | 'failed'>('idle');

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (reason.trim().length < 5) { setFieldError(t('blocked.form.tooShort')); return; }
    setFieldError(''); setPhase('sending');
    try {
      // A dedicated access request: no scan, no reward. The security team answers it from the Security inbox.
      const res = await fetch('/api/access-requests', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, reason: reason.trim() }),
      });
      const body = await res.json().catch(() => ({}));
      setPhase(!res.ok ? 'failed' : body.duplicate ? 'duplicate' : 'sent');
    } catch { setPhase('failed'); }
  }

  const canRequest = Boolean(domain);
  const requestDone = phase === 'sent' || phase === 'duplicate';
  return (
    <SecurityScreen
      tone="blocked" area={t('blocked.area')} status={t('blocked.status')}
      icon={<ShieldBan size={36} strokeWidth={1.6} />}
      eyebrow={t('blocked.eyebrow')} title={t('blocked.hero.title')}
      lead={<>{t(reasonKey(params.get('reason')))} {t('blocked.private')}</>}
      heroExtra={<div className="sec-target"><span>{t('blocked.destination')}</span><strong>{domain ?? t('blocked.noAddress')}</strong></div>}
      actions={<>
        {canRequest && (isAuthenticated || isLoading
          ? <button type="button" className="btn btn-light" aria-expanded={formOpen} aria-controls="request-access" onClick={() => setFormOpen(open => !open)} disabled={requestDone}>{t('blocked.requestAccess')}</button>
          : <Link className="btn btn-light" href="/auth">{t('blocked.signIn')}</Link>)}
        <Link className="btn btn-ghost" href="/">{t('blocked.goDashboard')}</Link>
      </>}
      guideEyebrow={t('blocked.next')} guideTitle={t('blocked.need')} guideId="blocked-next"
      footerLeft={t('blocked.brandLine')} footerRight={t('blocked.footer')}
    >
      <ol className="sec-steps">
        <li><span className="sec-step-icon" aria-hidden="true"><FileSearch size={20} /></span><div><small>01</small><h3>{t('blocked.s1.title')}</h3><p>{t('blocked.help')}</p></div></li>
        <li><span className="sec-step-icon" aria-hidden="true"><Flag size={20} /></span><div><small>02</small><h3>{t('blocked.s2.title')}</h3><p>{t('blocked.form.hint')}</p></div></li>
      </ol>
      {canRequest && !isAuthenticated && !isLoading && <p className="sec-help">{t('blocked.signInHint')}</p>}

      {formOpen && isAuthenticated && !requestDone && (
        <form id="request-access" className="sec-request" onSubmit={send} noValidate>
          <Field label={t('blocked.form.label')} error={fieldError || undefined}>
            {control => <textarea {...control} rows={3} maxLength={1000} autoFocus placeholder={t('blocked.form.placeholder')} value={reason} onChange={e => { setReason(e.target.value); if (fieldError) setFieldError(''); }} />}
          </Field>
          {phase === 'failed' && <div className="sec-banner" data-tone="bad" role="alert"><strong>{t('blocked.fail.title')}</strong>{t('blocked.fail.body')}</div>}
          <button className="btn btn-primary" disabled={phase === 'sending'}>{phase === 'sending' ? t('blocked.form.sending') : t('blocked.form.send')}</button>
        </form>
      )}
      {phase === 'duplicate' && <div className="sec-banner" data-tone="ok" role="status"><strong>{t('blocked.dup.title')}</strong>{t('blocked.dup.body', { domain: domain ?? '' })}</div>}
      {phase === 'sent' && <div className="sec-banner" data-tone="ok" role="status"><strong>{t('blocked.sent.title')}</strong>{t('blocked.sent.body', { domain: domain ?? '' })}</div>}

      <div className="sec-note"><LockKeyhole size={18} aria-hidden="true" /><p>{t('blocked.note')}</p></div>
    </SecurityScreen>
  );
}

export default function BlockedPage() {
  return <Suspense fallback={<div className="sec-page"><StateMessage variant="loading" /></div>}><BlockedContent /></Suspense>;
}
