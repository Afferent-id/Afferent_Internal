'use client';

import { useCallback, useMemo, useState, useSyncExternalStore } from 'react';
import ProxyOperationsSection from '@/components/admin/ProxyOperationsSection';
import ThreatCacheSection from '@/components/admin/ThreatCacheSection';
import LoginHistorySection from '@/components/admin/LoginHistorySection';
import Tabs, { panelId, tabId } from '@/components/ui/Tabs';
import { useI18n } from '@/i18n/I18nProvider';
import { searchForView, threatsNeedingAttention, viewFromSearch, type TrafficView } from '@/lib/trafficView';
import type { ThreatCacheEntry, AdminLoginEvent } from '@/components/admin/types';
import type { LoadState } from '@/lib/loadState';

const PREFIX = 'traffic';
const VIEW_EVENT = 'afferent:view';

function subscribe(notify: () => void) {
  window.addEventListener('popstate', notify);
  window.addEventListener(VIEW_EVENT, notify);
  return () => { window.removeEventListener('popstate', notify); window.removeEventListener(VIEW_EVENT, notify); };
}

interface TrafficPoliciesProps {
  cacheData: ThreatCacheEntry[];
  cacheState?: LoadState;
  threatTypeFilter: string;
  threatActionFilter: string;
  onThreatTypeFilterChange: (value: string) => void;
  onThreatActionFilterChange: (value: string) => void;
  loginHistory: AdminLoginEvent[];
  loginState?: LoadState;
}

/**
 * One page, four sub-tabs: the decision queue first, then policies, the threat feed and sign-in history.
 * The summary strip and the tab row stay on screen; badges show what needs attention so nothing important hides in a tab.
 * The selected tab lives in `?view=` so links and the Back button work. No new data and no new requests.
 */
export default function TrafficPolicies(props: TrafficPoliciesProps) {
  const { t } = useI18n();
  const [openAlerts, setOpenAlerts] = useState(0);
  const search = useSyncExternalStore(subscribe, () => window.location.search, () => '');
  const view: TrafficView = viewFromSearch(search);

  const select = useCallback((next: string) => {
    const target = next as TrafficView;
    if (target === viewFromSearch(window.location.search)) return;
    window.history.pushState(null, '', `${window.location.pathname}${searchForView(target)}`);
    window.dispatchEvent(new Event(VIEW_EVENT));
  }, []);

  const threats = threatsNeedingAttention(props.cacheData);
  const tabs = useMemo(() => [
    { id: 'live', label: t('traffic.tab.live'), badge: openAlerts, badgeLabel: t('traffic.badge.alerts', { n: openAlerts }) },
    { id: 'policies', label: t('traffic.tab.policies') },
    { id: 'threats', label: t('traffic.tab.threats'), badge: threats, badgeLabel: t('traffic.badge.threats', { n: threats }) },
    { id: 'audit', label: t('traffic.tab.audit') },
  ], [t, openAlerts, threats]);

  const tabRow = <Tabs label={t('traffic.tabs.label')} tabs={tabs} selected={view} onSelect={select} idPrefix={PREFIX} />;
  const other = view === 'threats' || view === 'audit';

  return (
    <ProxyOperationsSection view={other ? 'other' : view} tabs={tabRow} onOpenAlerts={setOpenAlerts}>
      {view === 'threats' && (
        <div role="tabpanel" id={panelId(PREFIX, 'threats')} aria-labelledby={tabId(PREFIX, 'threats')}>
          <ThreatCacheSection readOnly={false} state={props.cacheState} cacheData={props.cacheData} threatTypeFilter={props.threatTypeFilter} threatActionFilter={props.threatActionFilter} onThreatTypeFilterChange={props.onThreatTypeFilterChange} onThreatActionFilterChange={props.onThreatActionFilterChange} />
        </div>
      )}
      {view === 'audit' && (
        <div role="tabpanel" id={panelId(PREFIX, 'audit')} aria-labelledby={tabId(PREFIX, 'audit')}>
          <LoginHistorySection readOnly={false} loginHistory={props.loginHistory} state={props.loginState} />
        </div>
      )}
    </ProxyOperationsSection>
  );
}
