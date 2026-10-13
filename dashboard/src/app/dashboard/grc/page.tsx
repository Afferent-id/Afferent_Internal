'use client';

import { useState } from 'react';
import DashboardLayout from '@/components/admin/DashboardLayout';
import OverviewSection from '@/components/admin/OverviewSection';
import LeaderboardSection from '@/components/admin/LeaderboardSection';
import EmployeeRosterSection from '@/components/admin/EmployeeRosterSection';
import { usePolling } from '@/hooks/usePolling';
import { useFetchOnce } from '@/hooks/useFetchOnce';
import { loadState } from '@/lib/loadState';
import type { Incident, Stats, ThreatCacheEntry, AISummary, BehaviorScore, ComplianceSummary, LeaderboardResponse, EmployeeAccount, Division } from '@/components/admin/types';
import { ComplianceReadinessSection } from '@/components/admin/ComplianceReadinessSection';
import AuditLogSection from '@/components/admin/AuditLogSection';
import AIIntelligenceSection from '@/components/admin/AIIntelligenceSection';
import SecurityInboxSection from '@/components/admin/SecurityInboxSection';

const pickEmployees = (json: unknown): EmployeeAccount[] => (Array.isArray(json) ? json : (json as { employees?: EmployeeAccount[] })?.employees || []);
const pickDivisions = (json: unknown): Division[] => (Array.isArray(json) ? json : (json as { divisions?: Division[] })?.divisions || []);

export default function GCDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [divisiFilter, setDivisiFilter] = useState('ALL');
  const [badgeFilter, setBadgeFilter] = useState('ALL');

  const { data: incidentData, hasUpdated: incidentUpdated, isLoading: incidentsLoading, error: incidentsError, refresh: refreshIncidents } = usePolling<{ incidents: Incident[]; stats: Stats }>('/api/incident', 3000);
  const { data: cacheData, hasUpdated: cacheUpdated } = usePolling<{ cache: ThreatCacheEntry[] }>('/api/cache', 3000);
  const { data: summaryData, hasUpdated: summaryUpdated, isLoading: summaryLoading, error: summaryError, refresh: refreshSummary } = usePolling<{ summaries: AISummary[] }>('/api/summary', 3000);
  const { data: behaviorData, hasUpdated: behaviorUpdated, isLoading: behaviorLoading, error: behaviorError, refresh: refreshBehavior } = usePolling<{ scores: BehaviorScore[] }>('/api/behavior', 3000);
  const { data: complianceData } = usePolling<ComplianceSummary>('/api/admin/compliance-summary', 3000);
  const { data: leaderboardData, isLoading: leaderboardLoading, error: leaderboardError, refresh: refreshLeaderboard } = usePolling<LeaderboardResponse>('/api/admin/leaderboard', 3000);

  const { data: employees, state: rosterState } = useFetchOnce<EmployeeAccount[]>('/api/admin/employees', pickEmployees, []);
  const { data: divisions } = useFetchOnce<Division[]>('/api/admin/divisions', pickDivisions, []);

  const incidents = incidentData?.incidents || [];
  const activeIncidents = incidents.filter(inc => inc.status !== 'closed');

  return (
    <DashboardLayout role="grc" activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'inbox' && <SecurityInboxSection canDecideAccess={false} />}
      {activeTab === 'overview' && (
        <OverviewSection
          readOnly={true}
          stats={incidentData?.stats}
          incidents={activeIncidents}
          summaries={summaryData?.summaries || []}
          scores={behaviorData?.scores || []}
          cache={cacheData?.cache || []}
          complianceData={complianceData}
          incidentsState={loadState(incidentsLoading, incidentsError, incidentData !== null, refreshIncidents)}
          scoresState={loadState(behaviorLoading, behaviorError, behaviorData !== null, refreshBehavior)}
          summariesState={loadState(summaryLoading, summaryError, summaryData !== null, refreshSummary)}
          incidentUpdated={incidentUpdated}
          cacheUpdated={cacheUpdated}
          summaryUpdated={summaryUpdated}
          behaviorUpdated={behaviorUpdated}
        />
      )}

      {activeTab === 'leaderboard' && (
        <LeaderboardSection
          readOnly={false}
          leaderboardData={leaderboardData}
          state={loadState(leaderboardLoading, leaderboardError, leaderboardData !== null, refreshLeaderboard)}
          divisiFilter={divisiFilter}
          badgeFilter={badgeFilter}
          onDivisiFilterChange={setDivisiFilter}
          onBadgeFilterChange={setBadgeFilter}
        />
      )}

      {activeTab === 'compliance' && (
        <ComplianceReadinessSection readOnly={false} />
      )}

      {activeTab === 'audit' && <AuditLogSection />}
      {activeTab === 'ai' && (
        <AIIntelligenceSection role="grc" readOnly={false} />
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
    </DashboardLayout>
  );
}
