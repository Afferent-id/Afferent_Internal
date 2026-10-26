'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import { BookOpen, Check, ChevronDown, Copy, Download, Globe2, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react';
import Dialog from '@/components/ui/Dialog';
import type { MessageKey } from '@/i18n/messages';
import { knownServerMessage } from '@/lib/serverError';
import { protectionBlockVisible } from '@/lib/requestNotices';
import { formatAgo } from '@/lib/relativeTime';
import { useNow } from '@/hooks/useNow';

type ProxyStatus = {
  registered: boolean;
  connected: boolean;
  deviceId?: string;
  label?: string;
  sourceIpHint?: string;
  lastProxySeenAt?: string | null;
};

type ProbeState = 'checking' | 'connected' | 'disconnected';

async function probeSystemProxy(url: string) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2500);
  try {
    await fetch(`${url}${url.includes('?') ? '&' : '?'}nonce=${Date.now()}`, {
      cache: 'no-store',
      mode: 'no-cors',
      signal: controller.signal,
    });
    return true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function responseError(response: Response, fallback: string, t: (key: MessageKey) => string) {
  try {
    return knownServerMessage(await response.json(), t) ?? fallback;
  } catch {
    return fallback;
  }
}

/**
 * One connection status block, with technical details folded away.
 * Keep a verified connection visible without changing the existing probe or heartbeat.
 */
export default function ProxyConnectionCard() {
  const { t, lang } = useI18n();
  const now = useNow();
  const tRef = useRef(t);
  useEffect(() => { tRef.current = t; }, [t]);
  const [status, setStatus] = useState<ProxyStatus>({ registered: false, connected: false });
  const [proxyUrl, setProxyUrl] = useState('http://127.0.0.1:3128');
  const [proxyProbeUrl, setProxyProbeUrl] = useState('');
  const [probeState, setProbeState] = useState<ProbeState>('checking');
  const [apiBase, setApiBase] = useState('');
  const [booting, setBooting] = useState(true);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const deviceFetch = useCallback((path: string, options?: RequestInit) => fetch(
    `${apiBase}${path}`,
    { ...options, credentials: 'include' },
  ), [apiBase]);

  const loadStatus = useCallback(async () => {
    const configResponse = await fetch('/api/config', { cache: 'no-store' });
    const config = configResponse.ok ? await configResponse.json() : {};
    const runtimeApiBase = String(config.apiUrl || `${window.location.protocol}//${window.location.hostname}:5000`).replace(/\/$/, '');
    setApiBase(runtimeApiBase);
    if (config.proxyUrl) setProxyUrl(config.proxyUrl);
    setProxyProbeUrl(String(
      config.proxyProbeUrl || 'http://proxy-check.afferent.invalid/__afferent_probe__',
    ));
    const directFetch = (path: string, options?: RequestInit) => fetch(
      `${runtimeApiBase}${path}`,
      { ...options, credentials: 'include' },
    );
    const statusResponse = await directFetch('/api/proxy/device/status', { cache: 'no-store' });
    if (!statusResponse.ok) {
      throw new Error(await responseError(
        statusResponse,
        statusResponse.status === 401
          ? tRef.current('proxy.err.session')
          : tRef.current('proxy.err.status'),
        tRef.current,
      ));
    }
    const statusPayload = await statusResponse.json();
    let currentStatus = statusPayload?.status as ProxyStatus | undefined;
    if (!currentStatus) throw new Error(tRef.current('proxy.err.status'));
    if (!currentStatus.registered) {
      const registration = await directFetch('/api/proxy/device/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: 'Perangkat utama' }),
      });
      if (!registration.ok) {
        throw new Error(await responseError(registration, tRef.current('proxy.err.activate'), tRef.current));
      }
      const registered = (await registration.json())?.status as ProxyStatus | undefined;
      if (!registered) throw new Error(tRef.current('proxy.err.activate'));
      currentStatus = registered;
    }
    setStatus(currentStatus);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStatus()
        .then(() => setError(''))
        .catch((err) => setError(err instanceof Error ? err.message : tRef.current('proxy.err.unavailable')))
        .finally(() => setBooting(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadStatus]);

  useEffect(() => {
    if (!proxyProbeUrl) return;
    let active = true;
    const probe = async () => {
      const connected = await probeSystemProxy(proxyProbeUrl);
      if (active) setProbeState(connected ? 'connected' : 'disconnected');
    };
    // Preserve the verified ON/OFF probe; reset when its network target changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProbeState('checking');
    void probe();
    const timer = window.setInterval(() => void probe(), 5_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [proxyProbeUrl]);

  useEffect(() => {
    if (!status.registered) return;
    const heartbeat = async () => {
      try {
        const response = await deviceFetch('/api/proxy/device/heartbeat', { method: 'POST' });
        if (response.ok) {
          setStatus((await response.json()).status);
          setError('');
        } else {
          setError(await responseError(response, tRef.current('proxy.err.lost'), tRef.current));
        }
      } catch {
        setError(tRef.current('proxy.err.lost'));
      }
    };
    const timer = window.setInterval(() => void heartbeat(), 10_000);
    return () => window.clearInterval(timer);
  }, [deviceFetch, status.registered]);

  const activate = async () => {
    setActivating(true);
    setError('');
    try {
      const response = await deviceFetch('/api/proxy/device/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: 'Perangkat utama' }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(knownServerMessage(payload, tRef.current) ?? tRef.current('proxy.err.activate'));
      setStatus(payload.status);
    } catch (err) {
      setError(err instanceof Error ? err.message : tRef.current('proxy.err.activate'));
    } finally {
      setActivating(false);
    }
  };

  const copyProxy = async () => {
    // Some browsers refuse clipboard writes (no permission, insecure page). The address stays visible to copy by hand.
    try {
      await navigator.clipboard.writeText(proxyUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch { /* nothing to do: the address is on screen */ }
  };

  const visible = protectionBlockVisible({ booting, failedToLoad: Boolean(error), registered: status.registered, probe: probeState });
  const connected = status.registered && probeState === 'connected' && !error;
  const title = connected ? t('proxy.on.title') : status.registered ? t('proxy.failed.title') : t('proxy.off.title');
  const body = connected ? t('proxy.on.body') : status.registered ? t('proxy.failed.body') : t('proxy.setup.body');
  const lastChecked = status.lastProxySeenAt ? formatAgo(status.lastProxySeenAt, lang, now) : null;

  return (
    <>
      {visible && (
        <section className="proxy-connect-card pxc pxc-alert" data-tone={connected ? 'ok' : 'bad'} aria-labelledby="pxc-title">
          <div className="pxc-head">
            <div className="pxc-main">
              <span className="pxc-icon" aria-hidden="true">{connected ? <ShieldCheck size={22} /> : <ShieldAlert size={22} />}</span>
              <div>
                <p className="pxc-eyebrow">{t('proxy.eyebrow')}</p>
                <div role="status">
                  <h2 id="pxc-title">{title}</h2>
                  <p>{body}</p>
                </div>
                {error && <p className="field-error" role="alert">{error}</p>}
              </div>
            </div>
            {status.registered
              ? <button type="button" className={connected ? 'btn' : 'btn btn-primary'} onClick={() => setGuideOpen(true)}><BookOpen size={16} aria-hidden="true" />{t('setup.open')}</button>
              : <button type="button" className="btn btn-primary" onClick={activate} disabled={activating || booting}>
                  {activating ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <ShieldCheck size={16} aria-hidden="true" />}
                  {t('emp.next.protect.action')}
                </button>}
          </div>
          <details className="pxc-details">
            <summary><ChevronDown size={14} aria-hidden="true" />{t('proxy.details')}</summary>
            <div className="pxc-actions">
              <span className="emp-muted">{t('proxy.address')}</span>
              <button type="button" className="pxc-address" onClick={copyProxy} title={t('proxy.copy')} aria-label={`${proxyUrl}. ${t('proxy.copy')}`}>
                <Globe2 size={15} aria-hidden="true" /> <span>{proxyUrl}</span> {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
              </button>
              <a href="/api/proxy/ca.crt" download="afferent-proxy-ca.crt" className="btn" title={t('proxy.ca.hint')}>
                <Download size={14} aria-hidden="true" /> {t('proxy.ca')}
              </a>
              {status.registered || <button type="button" className="btn" onClick={() => setGuideOpen(true)}><BookOpen size={14} aria-hidden="true" /> {t('setup.open')}</button>}
            </div>
            <p className="pxc-facts emp-muted">
              {status.registered && <span>{t('proxy.ip', { ip: status.sourceIpHint || t('proxy.ip.stored') })}</span>}
              {lastChecked && <span>{t('proxy.lastChecked', { time: lastChecked })}</span>}
            </p>
          </details>
        </section>
      )}
      <SetupGuide open={guideOpen} onClose={() => setGuideOpen(false)} proxyUrl={proxyUrl} />
    </>
  );
}

type Device = 'windows' | 'macos' | 'ios' | 'android';
const DEVICES: Device[] = ['windows', 'macos', 'ios', 'android'];

/** Plain steps, one device at a time. The address is shown at the step that needs it. */
function SetupGuide({ open, onClose, proxyUrl }: { open: boolean; onClose: () => void; proxyUrl: string }) {
  const { t } = useI18n();
  const [device, setDevice] = useState<Device>('windows');
  const steps: MessageKey[] = ['setup.s1', 'setup.s2', `setup.${device}.s3` as MessageKey, `setup.${device}.s4` as MessageKey, 'setup.s5'];
  return (
    <Dialog open={open} onClose={onClose} size="lg" title={t('setup.title')} description={t('setup.desc')}
      footer={<button type="button" className="btn btn-primary" onClick={onClose}>{t('setup.done')}</button>}>
      <div className="seg" role="group" aria-label={t('setup.tabs')} style={{ flexWrap: 'wrap' }}>
        {DEVICES.map(item => <button key={item} type="button" aria-pressed={device === item} onClick={() => setDevice(item)}>{t(`setup.os.${item}` as MessageKey)}</button>)}
      </div>
      <ol className="setup-steps">
        {steps.map(step => <li key={step}>{t(step)}</li>)}
      </ol>
      <p className="setup-address"><span className="emp-muted">{t('setup.address')}</span> <code>{proxyUrl}</code></p>
      <p className="emp-muted">{t('setup.help')}</p>
    </Dialog>
  );
}
