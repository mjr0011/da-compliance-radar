'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Company } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import {
  RiskPill,
  ScoreBar,
  TableSkeleton,
  Empty,
  ErrorState,
} from '@/components/ui';
import { formatDate, formatRelative } from '@/lib/format';
import { RefreshCw, Search, Building2 } from 'lucide-react';

export default function CompaniesPage() {
  const [q, setQ] = useState('');
  const [sicPrefix, setSicPrefix] = useState('');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [minLeadScore, setMinLeadScore] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 25;

  const qc = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['companies', { q, sicPrefix, overdueOnly, minLeadScore, page }],
    queryFn: () =>
      api.listCompanies({
        q: q || undefined,
        sic_prefix: sicPrefix || undefined,
        overdue_only: overdueOnly,
        min_lead_score: minLeadScore || undefined,
        limit,
        offset: page * limit,
      }),
    placeholderData: (p) => p,
  });

  const refreshMutation = useMutation({
    mutationFn: (n: string) => api.refreshCompany(n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['companies'] }),
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Pipeline"
        title="Companies"
        description="Every UK company being tracked. Filter by location, sector, risk or score. Click refresh to re-pull from Companies House."
      />

      <div className="px-6 lg:px-10 py-8 space-y-6">
        {/* Filters */}
        <div className="card p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[1fr_140px_120px_auto_auto] gap-3 items-end">
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-navy-400" />
              <input
                value={q}
                onChange={(e) => { setQ(e.target.value); setPage(0); }}
                placeholder="Name or company number"
                className="input pl-8"
              />
            </div>
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              SIC prefix
            </label>
            <input
              value={sicPrefix}
              onChange={(e) => { setSicPrefix(e.target.value); setPage(0); }}
              placeholder="e.g. 43"
              className="input"
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
              Min lead score
            </label>
            <input
              type="number" min={0} max={100}
              value={minLeadScore || ''}
              onChange={(e) => { setMinLeadScore(Number(e.target.value) || 0); setPage(0); }}
              className="input tabular-nums"
              placeholder="0"
            />
          </div>
          <label className="flex items-center gap-2 px-3 py-2 cursor-pointer text-sm select-none">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => { setOverdueOnly(e.target.checked); setPage(0); }}
              className="w-4 h-4 accent-navy-700"
            />
            <span>Overdue only</span>
          </label>
          <div className="text-xs text-navy-500 tabular-nums lg:text-right">
            {data ? `${data.total.toLocaleString('en-GB')} matches` : '—'}
          </div>
        </div>

        {error ? (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        ) : isLoading && !data ? (
          <TableSkeleton rows={8} cols={6} />
        ) : !data || data.items.length === 0 ? (
          <Empty
            icon={Building2}
            title="No companies match"
            description="Adjust filters above, or trigger the worker to discover companies via the Companies House refresh endpoint."
          />
        ) : (
          <>
            {/* Desktop table */}
            <div className="card overflow-hidden hidden md:block fade-up">
              <table className="w-full text-sm">
                <thead className="bg-navy-50 border-b border-navy-200/60">
                  <tr className="text-[11px] uppercase tracking-wider2 text-navy-500">
                    <th className="text-left font-medium px-5 py-3">Company</th>
                    <th className="text-left font-medium px-5 py-3">Sector</th>
                    <th className="text-left font-medium px-5 py-3">Location</th>
                    <th className="text-left font-medium px-5 py-3">Risk</th>
                    <th className="text-left font-medium px-5 py-3">Lead score</th>
                    <th className="text-left font-medium px-5 py-3">Next deadline</th>
                    <th className="text-right font-medium px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-200/40">
                  {data.items.map((c) => (
                    <CompanyRow
                      key={c.id}
                      company={c}
                      onRefresh={() => refreshMutation.mutate(c.company_number)}
                      refreshing={refreshMutation.isPending && refreshMutation.variables === c.company_number}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3 fade-up">
              {data.items.map((c) => (
                <CompanyCardMobile
                  key={c.id}
                  company={c}
                  onRefresh={() => refreshMutation.mutate(c.company_number)}
                  refreshing={refreshMutation.isPending && refreshMutation.variables === c.company_number}
                />
              ))}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between text-sm pt-2 flex-wrap gap-3">
              <div className="text-navy-500">
                Showing {data.offset + 1}–{Math.min(data.offset + data.items.length, data.total)}
                {' '}of {data.total.toLocaleString('en-GB')}
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="btn-ghost disabled:opacity-30"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >← Prev</button>
                <button
                  className="btn-ghost disabled:opacity-30"
                  disabled={data.offset + data.items.length >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                >Next →</button>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function CompanyRow({
  company,
  onRefresh,
  refreshing,
}: {
  company: Company;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const c = company.compliance;
  return (
    <tr className="hover:bg-cream-50/40 transition-colors">
      <td className="px-5 py-3">
        <div className="font-medium text-navy-900">{company.company_name}</div>
        <div className="font-mono text-[11px] text-navy-500 mt-0.5">
          {company.company_number}
          {company.status && <> · {company.status}</>}
        </div>
      </td>
      <td className="px-5 py-3 text-navy-600 text-xs">
        {company.sic_description || company.sic_code || '—'}
      </td>
      <td className="px-5 py-3 text-navy-600 text-xs">
        {company.locality || company.postal_code || '—'}
      </td>
      <td className="px-5 py-3">
        <RiskPill level={c?.risk_level} />
      </td>
      <td className="px-5 py-3">
        <ScoreBar score={company.lead_score} />
      </td>
      <td className="px-5 py-3 text-xs">
        {c?.next_deadline ? (
          <>
            <div className="text-navy-900">{formatDate(c.next_deadline)}</div>
            <div className="text-navy-500">{formatRelative(c.next_deadline)}</div>
          </>
        ) : (
          <span className="text-navy-400">—</span>
        )}
      </td>
      <td className="px-5 py-3 text-right">
        <button
          onClick={onRefresh}
          disabled={refreshing}
          title="Re-pull from Companies House"
          className="btn-ghost"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </td>
    </tr>
  );
}

function CompanyCardMobile({
  company,
  onRefresh,
  refreshing,
}: {
  company: Company;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const c = company.compliance;
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="min-w-0 flex-1">
          <div className="font-medium text-navy-900 truncate">{company.company_name}</div>
          <div className="font-mono text-[11px] text-navy-500 mt-0.5">
            {company.company_number}
          </div>
        </div>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="btn-ghost shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>
      <div className="text-xs text-navy-600 mb-3">
        {company.sic_description || company.sic_code || '—'}
        {company.locality && <> · {company.locality}</>}
      </div>
      <div className="flex items-center justify-between gap-3">
        <RiskPill level={c?.risk_level} />
        <ScoreBar score={company.lead_score} />
      </div>
      {c?.next_deadline && (
        <div className="mt-3 pt-3 border-t border-navy-200/40 text-xs flex justify-between">
          <span className="text-navy-500">Next deadline</span>
          <span className="text-navy-900">{formatDate(c.next_deadline)} · {formatRelative(c.next_deadline)}</span>
        </div>
      )}
    </div>
  );
}
