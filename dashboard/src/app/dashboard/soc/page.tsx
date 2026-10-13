'use client';

import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/admin/DashboardLayout';
import { useI18n } from '@/i18n/I18nProvider';
import OverviewSection from '@/components/admin/OverviewSection';
import IncidentQueue from '@/components/admin/IncidentQueue';
import { usePolling } from '@/hooks/usePolling';
import { useFetchOnce } from '@/hooks/useFetchOnce';
import { loadState } from '@/lib/loadState';
import type { Incident, Stats, ThreatCacheEntry, AISummary, BehaviorScore, ComplianceSummary, AdminLoginEvent } from '@/components/admin/types';
import AuditLogSection from '@/components/admin/AuditLogSection';
import AIIntelligenceSection from '@/components/admin/AIIntelligenceSection';
import SecurityInboxSection from '@/components/admin/SecurityInboxSection';
import TrafficPolicies from '@/components/admin/TrafficPolicies';

export default function SOCDashboard() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState('overview');
  // A link such as /dashboard/soc?view=policies opens Traffic and policies straight away.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (new URLSearchParams(window.location.search).has('view')) setActiveTab('threats');
  }, []);
  const changeTab = (tab: string) => {
    setActiveTab(tab);
    if (tab !== 'threats' && window.location.search) window.history.replaceState(null, '', window.location.pathname);
  };
  const [threatTypeFilter, setThreatTypeFilter] = useState('ALL');
  const [threatActionFilter, setThreatActionFilter] = useState('ALL');

  // Polling core data
  const { data: incidentData, hasUpdated: incidentUpdated, isLoading: incidentsLoading, error: incidentsError, refresh: refreshIncidents } = usePolling<{ incidents: Incident[]; stats: Stats }>('/api/incident', 3000);
  const { data: cacheData, hasUpdated: cacheUpdated, isLoading: cacheLoading, error: cacheError, refresh: refreshCache } = usePolling<{ cache: ThreatCacheEntry[] }>('/api/cache', 3000);
  const { data: summaryData, hasUpdated: summaryUpdated, refresh: refreshSummary, error: summaryError, isLoading: summaryLoading } = usePolling<{ summaries: AISummary[] }>('/api/summary', 10000);
  const { data: behaviorData, hasUpdated: behaviorUpdated, error: behaviorError, isLoading: behaviorLoading, refresh: refreshBehavior } = usePolling<{ scores: BehaviorScore[] }>('/api/behavior', 10000);
  const { data: complianceData } = usePolling<ComplianceSummary>('/api/admin/compliance-summary', 3000);

  const { data: loginHistory, state: loginState } = useFetchOnce<AdminLoginEvent[]>('/api/admin/login-history', json => (Array.isArray(json) ? json : (json as { logs?: AdminLoginEvent[] })?.logs || []), []);

  const incidents = incidentData?.incidents || [];
  const activeIncidents = incidents.filter(inc => inc.status !== 'closed');
  const cache = cacheData?.cache || [];
  const summaries = summaryData?.summaries || [];
  const scores = behaviorData?.scores || [];

  return (
    <DashboardLayout role="soc" activeTab={activeTab} onTabChange={changeTab}>
      {activeTab === 'overview' && (
        <>
          <IncidentQueue incidents={incidents} canResolve onChanged={refreshIncidents} loading={incidentsLoading} error={Boolean(incidentsError) && !incidentData} />
          {(summaryError || behaviorError) && <p className="debt-error" role="alert">{t('soc.err.telemetry')}</p>}
          <OverviewSection
            onRefreshSummary={refreshSummary}
            readOnly={false}
            stats={incidentData?.stats}
            incidents={activeIncidents}
            summaries={summaries}
            scores={scores}
            cache={cache}
            complianceData={complianceData}
            incidentsState={loadState(incidentsLoading, incidentsError, incidentData !== null, refreshIncidents)}
            scoresState={loadState(behaviorLoading, behaviorError, behaviorData !== null, refreshBehavior)}
            summariesState={loadState(summaryLoading, summaryError, summaryData !== null, refreshSummary)}
            incidentUpdated={incidentUpdated}
            cacheUpdated={cacheUpdated}
            summaryUpdated={summaryUpdated}
            behaviorUpdated={behaviorUpdated}
          />
        </>
      )}

      {activeTab === 'threats' && (
        <TrafficPolicies
          cacheData={cache}
          cacheState={loadState(cacheLoading, cacheError, cacheData !== null, refreshCache)}
          threatTypeFilter={threatTypeFilter}
          threatActionFilter={threatActionFilter}
          onThreatTypeFilterChange={setThreatTypeFilter}
          onThreatActionFilterChange={setThreatActionFilter}
          loginHistory={loginHistory}
          loginState={loginState}
        />
      )}

      {activeTab === 'audit' && <AuditLogSection />}
      {activeTab === 'ai' && (
        <AIIntelligenceSection role="soc" readOnly={false} />
      )}
      {activeTab === 'inbox' && <SecurityInboxSection canDecideAccess={true} />}
    </DashboardLayout>
  );
}
