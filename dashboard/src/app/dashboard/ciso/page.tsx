'use client';

import { useState } from 'react';
import DashboardLayout from '@/components/admin/DashboardLayout';
import OverviewSection from '@/components/admin/OverviewSection';
import IncidentQueue from '@/components/admin/IncidentQueue';
import ExecutiveSummary from '@/components/admin/ExecutiveSummary';
import { useI18n } from '@/i18n/I18nProvider';
import ThreatCacheSection from '@/components/admin/ThreatCacheSection';
import LeaderboardSection from '@/components/admin/LeaderboardSection';
import PolicySection from '@/components/admin/PolicySection';
import GophishCampaignSection from '@/components/admin/GophishCampaignSection';
import EmployeeRosterSection from '@/components/admin/EmployeeRosterSection';
import { usePolling } from '@/hooks/usePolling';
import { useFetchOnce } from '@/hooks/useFetchOnce';
import { loadState } from '@/lib/loadState';
import type { Incident, Stats, ThreatCacheEntry, AISummary, BehaviorScore, PolicyDecision, ComplianceSummary, GoPhishCampaign, LeaderboardResponse, EmployeeAccount, Division } from '@/components/admin/types';

import AuditLogSection from '@/components/admin/AuditLogSection';
import AIIntelligenceSection from '@/components/admin/AIIntelligenceSection';

const pickCampaigns = (json: unknown): GoPhishCampaign[] => (Array.isArray(json) ? json : (json as { campaigns?: GoPhishCampaign[] })?.campaigns || []);
const pickEmployees = (json: unknown): EmployeeAccount[] => (Array.isArray(json) ? json : (json as { employees?: EmployeeAccount[] })?.employees || []);
const pickDivisions = (json: unknown): Division[] => (Array.isArray(json) ? json : (json as { divisions?: Division[] })?.divisions || []);

export default function CISODashboard() {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState('overview');

  // Polling core data
  const { data: incidentData, hasUpdated: incidentUpdated, isLoading: incidentsLoading, error: incidentsError, refresh: refreshIncidents } = usePolling<{ incidents: Incident[]; stats: Stats }>('/api/incident', 3000);
  const { data: cacheData, hasUpdated: cacheUpdated, isLoading: cacheLoading, error: cacheError, refresh: refreshCache } = usePolling<{ cache: ThreatCacheEntry[] }>('/api/cache', 3000);
  const { data: summaryData, hasUpdated: summaryUpdated, isLoading: summaryLoading, error: summaryError, refresh: refreshSummary } = usePolling<{ summaries: AISummary[] }>('/api/summary', 3000);
  const { data: behaviorData, hasUpdated: behaviorUpdated, isLoading: behaviorLoading, error: behaviorError, refresh: refreshBehavior } = usePolling<{ scores: BehaviorScore[] }>('/api/behavior', 3000);
  const { data: policyData, isLoading: policyLoading, error: policyError, refresh: refreshPolicy } = usePolling<{ decisions: PolicyDecision[] }>('/api/policy', 3000);
  const { data: complianceData } = usePolling<ComplianceSummary>('/api/admin/compliance-summary', 3000);
  const { data: leaderboardData, isLoading: leaderboardLoading, error: leaderboardError, refresh: refreshLeaderboard } = usePolling<LeaderboardResponse>('/api/admin/leaderboard', 3000);

  const { data: campaigns, state: campaignsState } = useFetchOnce<GoPhishCampaign[]>('/api/admin/gophish/campaigns', pickCampaigns, []);
  const { data: employees, state: rosterState } = useFetchOnce<EmployeeAccount[]>('/api/admin/employees', pickEmployees, []);
  const { data: divisions } = useFetchOnce<Division[]>('/api/admin/divisions', pickDivisions, []);

  const incidents = incidentData?.incidents || [];
  const activeIncidents = incidents.filter(inc => inc.status !== 'closed');
  const cache = cacheData?.cache || [];
  const summaries = summaryData?.summaries || [];
  const scores = behaviorData?.scores || [];
  const decisions = policyData?.decisions || [];

  return (
    <DashboardLayout role="ciso" activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'overview' && (
        <>
          <ExecutiveSummary incidents={incidents} scores={scores} compliance={complianceData} campaigns={campaigns}
            state={loadState(incidentsLoading || behaviorLoading, (incidentsError && !incidentData) || (behaviorError && !behaviorData), incidentData !== null && behaviorData !== null, () => { refreshIncidents(); refreshBehavior(); })} />
          <IncidentQueue incidents={incidents} canResolve={false} onChanged={refreshIncidents} loading={incidentsLoading} error={Boolean(incidentsError) && !incidentData} />
          <details className="exec-more">
            <summary>{t('exec.more')}<small>{t('exec.more.hint')}</small></summary>
            <div>
              <OverviewSection
                readOnly={true}
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
            </div>
          </details>
        </>
      )}

      {activeTab === 'threats' && (
        <ThreatCacheSection
          readOnly={true}
          state={loadState(cacheLoading, cacheError, cacheData !== null, refreshCache)}
          cacheData={cache}
          threatTypeFilter="ALL"
          threatActionFilter="ALL"
          onThreatTypeFilterChange={() => {}}
          onThreatActionFilterChange={() => {}}
        />
      )}

      {activeTab === 'leaderboard' && (
        <LeaderboardSection
          readOnly={true}
          leaderboardData={leaderboardData}
          state={loadState(leaderboardLoading, leaderboardError, leaderboardData !== null, refreshLeaderboard)}
          divisiFilter="ALL"
          badgeFilter="ALL"
          onDivisiFilterChange={() => {}}
          onBadgeFilterChange={() => {}}
        />
      )}

      {activeTab === 'policy' && (
        <PolicySection readOnly={true} decisions={decisions} state={loadState(policyLoading, policyError, policyData !== null, refreshPolicy)} />
      )}

      {activeTab === 'gophish' && (
        <GophishCampaignSection
          readOnly={true}
          campaigns={campaigns}
          campaignsState={campaignsState}
          employees={employees}
          divisions={divisions}
          resources={null}
          selectedEmails={[]}
          onSelectedEmailsChange={() => {}}
          onSyncUsers={() => {}}
          onOpenLaunchModal={() => {}}
          onDeleteCampaign={() => {}}
          onViewCampaignDetail={() => {}}
          onOpenTemplateBuilder={() => {}}
          onDeleteTemplate={() => {}}
          onDeletePage={() => {}}
        />
      )}

      {activeTab === 'employees' && (
        <EmployeeRosterSection
          readOnly={true}
          state={rosterState}
          employees={employees}
          divisions={divisions}
          onOpenAddEmployee={() => {}}
          onOpenEditEmployee={() => {}}
          onOpenAddDivision={() => {}}
        />
      )}

      {activeTab === 'audit' && <AuditLogSection />}
      {activeTab === 'ai' && (
        <AIIntelligenceSection role="ciso" readOnly={true} />
      )}
    </DashboardLayout>
  );
}
