'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, SuppressionEntry } from '@/lib/api';
import { AppShell, PageHeader } from '@/components/AppShell';
import { Empty, ErrorState, TableSkeleton } from '@/components/ui';
import { formatRelative } from '@/lib/format';
import { Shield, Plus, Trash2, X } from 'lucide-react';
import { clsx } from 'clsx';

const SOURCES = [
  'USER_OPT_OUT',
  'CTPS_MATCH',
  'CLIENT_REQUEST',
  'DSR_ERASURE',
  'MANUAL',
];

const SOURCE_LABELS: Record<string, string> = {
  USER_OPT_OUT: 'User opt-out',
  CTPS_MATCH: 'CTPS match',
  CLIENT_REQUEST: 'Client request',
  DSR_ERASURE: 'DSR erasure',
  MANUAL: 'Manual',
};

const SOURCE_COLORS: Record<string, string> = {
  USER_OPT_OUT: 'bg-accent/15 text-accent border-accent/30',
  CTPS_MATCH: 'bg-risk-high/10 text-risk-high border-risk-high/30',
  CLIENT_REQUEST: 'bg-navy-100 text-navy-700 border-navy-200',
  DSR_ERASURE: 'bg-risk-critical/10 text-risk-critical border-risk-critical/30',
  MANUAL: 'bg-navy-50 text-navy-700 border-navy-200',
};

export default function SuppressionPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['suppression'],
    queryFn: () => api.listSuppression({ limit: 200 }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteSuppression(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['suppression'] }),
  });

  const addMutation = useMutation({
    mutationFn: (body: Partial<SuppressionEntry>) => api.addSuppression(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['suppression'] });
      setShowForm(false);
    },
  });

  return (
    <AppShell>
      <PageHeader
        eyebrow="Admin"
        title="Suppression list"
        description="Companies, emails or domains that must never be contacted. Lookups gate lead creation, not just alerts — once suppressed, no outreach surface."
        actions={
          <button
            className="btn-primary"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? <><X className="w-3.5 h-3.5" /> Cancel</> : <><Plus className="w-3.5 h-3.5" /> Add entry</>}
          </button>
        }
      />

      <div className="px-6 lg:px-10 py-8 space-y-6">
        {showForm && (
          <AddSuppressionForm
            onSubmit={(body) => addMutation.mutate(body)}
            pending={addMutation.isPending}
            error={addMutation.error instanceof Error ? addMutation.error.message : null}
          />
        )}

        {error ? (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        ) : isLoading ? (
          <TableSkeleton rows={6} cols={5} />
        ) : !data || data.items.length === 0 ? (
          <Empty
            icon={Shield}
            title="Suppression list is empty"
            description="Add entries here as opt-outs come in, when a CTPS match is found, or when a data subject erasure request is processed."
          />
        ) : (
          <div className="card overflow-hidden fade-up">
            <table className="w-full text-sm">
              <thead className="bg-navy-50 border-b border-navy-200/60">
                <tr className="text-[11px] uppercase tracking-wider2 text-navy-500">
                  <th className="text-left font-medium px-5 py-3">Identifier</th>
                  <th className="text-left font-medium px-5 py-3">Source</th>
                  <th className="text-left font-medium px-5 py-3">Lawful basis / reason</th>
                  <th className="text-left font-medium px-5 py-3">Added</th>
                  <th className="text-right font-medium px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-200/40">
                {data.items.map((entry) => (
                  <tr key={entry.id} className="hover:bg-cream-50/40 transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-mono text-xs text-navy-900">
                        {entry.company_number && <span className="text-navy-700">CRN {entry.company_number}</span>}
                        {entry.email && <span>{entry.email}</span>}
                        {entry.domain && <span>@{entry.domain}</span>}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={clsx(
                        'pill border',
                        SOURCE_COLORS[entry.source] || 'bg-navy-100 text-navy-700 border-navy-200',
                      )}>
                        {SOURCE_LABELS[entry.source] || entry.source}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-xs">
                      {entry.lawful_basis && (
                        <div className="font-mono text-navy-700">{entry.lawful_basis}</div>
                      )}
                      {entry.reason && (
                        <div className="text-navy-600 max-w-xs truncate" title={entry.reason}>
                          {entry.reason}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3 text-xs">
                      <div className="text-navy-700">{entry.added_by || <span className="text-navy-400">system</span>}</div>
                      <div className="text-navy-500">{formatRelative(entry.created_at)}</div>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => {
                          if (confirm('Remove this suppression entry? Outreach to this entity will be permitted again.')) {
                            deleteMutation.mutate(entry.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="btn-ghost text-risk-critical"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function AddSuppressionForm({
  onSubmit,
  pending,
  error,
}: {
  onSubmit: (body: Partial<SuppressionEntry>) => void;
  pending: boolean;
  error: string | null;
}) {
  const [identifier, setIdentifier] = useState('');
  const [identifierType, setIdentifierType] = useState<'company_number' | 'email' | 'domain'>('company_number');
  const [source, setSource] = useState('USER_OPT_OUT');
  const [lawfulBasis, setLawfulBasis] = useState('');
  const [reason, setReason] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!identifier.trim()) return;
    onSubmit({
      [identifierType]: identifier.trim(),
      source,
      lawful_basis: lawfulBasis || undefined,
      reason: reason || undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="card p-5 fade-up">
      <div className="eyebrow mb-4">New suppression entry</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
            Identifier type
          </label>
          <select
            value={identifierType}
            onChange={(e) => setIdentifierType(e.target.value as 'company_number' | 'email' | 'domain')}
            className="input"
          >
            <option value="company_number">Company number</option>
            <option value="email">Email address</option>
            <option value="domain">Domain</option>
          </select>
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
            Identifier
          </label>
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder={identifierType === 'company_number' ? '12345678' : identifierType === 'email' ? 'user@example.com' : 'example.com'}
            className="input"
            required
          />
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
            Source
          </label>
          <select value={source} onChange={(e) => setSource(e.target.value)} className="input">
            {SOURCES.map((s) => <option key={s} value={s}>{SOURCE_LABELS[s]}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
            Lawful basis (optional)
          </label>
          <input
            value={lawfulBasis}
            onChange={(e) => setLawfulBasis(e.target.value)}
            placeholder="e.g. UK GDPR Art. 17(1)(c)"
            className="input"
          />
        </div>
        <div className="md:col-span-2">
          <label className="block text-[11px] uppercase tracking-wider2 text-navy-500 mb-1.5">
            Reason / notes
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why was this entity suppressed?"
            rows={2}
            className="input resize-none"
          />
        </div>
      </div>
      {error && (
        <div className="mt-3 text-xs text-risk-critical">{error}</div>
      )}
      <div className="flex justify-end mt-4">
        <button type="submit" disabled={pending || !identifier.trim()} className="btn-primary">
          {pending ? 'Saving…' : 'Add to suppression list'}
        </button>
      </div>
    </form>
  );
}
