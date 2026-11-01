import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { apiErrorMessage } from '../../services/api'
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '../Card'
import { LoadingSpinner, ErrorState, EmptyState } from '../Feedback'
import DataTable from '../DataTable'
import StatusBadge from '../StatusBadge'
import { ScoreIndicator } from '../RiskGauge'

// Filter predicates run against the real fields of
// GET /api/reviewer/cases -- nothing is derived or invented.
const FILTERS = {
  all: { label: 'All', test: () => true },
  high: { label: 'High Risk', test: (c) => c.risk_level === 'HIGH' },
  pending: { label: 'Pending', test: (c) => ['MANUAL_REVIEW', 'RISK_CALCULATED'].includes(c.status) },
  flagged: { label: 'Flagged', test: (c) => ['FLAGGED', 'REJECTED'].includes(c.status) },
  verified: { label: 'Verified', test: (c) => c.status === 'VERIFIED' },
}

export default function CaseQueue({ title = 'Case Queue', defaultFilter = 'all', showKpis = false }) {
  const navigate = useNavigate()
  const [cases, setCases] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState(defaultFilter)

  useEffect(() => {
    api.get('/reviewer/cases')
      .then((res) => setCases(res.data))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load the case queue.')))
      .finally(() => setLoading(false))
  }, [])

  const rows = useMemo(() => (cases || []).filter(FILTERS[filter].test).map((c) => ({ ...c, id: c.case_id })), [cases, filter])
  const count = (key) => (cases || []).filter(FILTERS[key].test).length

  if (loading) return <LoadingSpinner label="Loading case queue..." />
  if (error) return <ErrorState message={error} />

  return (
    <div>
      {showKpis && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Pending Review" value={count('pending')} tone="pending" />
          <StatCard label="High Risk" value={count('high')} tone="flagged" />
          <StatCard label="Verified" value={count('verified')} tone="verified" />
          <StatCard label="Flagged" value={count('flagged')} tone="flagged" />
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filter cases">
            {Object.entries(FILTERS).map(([key, f]) => (
              <button
                key={key}
                role="tab"
                aria-selected={filter === key}
                onClick={() => setFilter(key)}
                className={`rounded-lg border px-2.5 py-1 text-xs transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand ${
                  filter === key ? 'border-brand bg-brand-soft text-brand' : 'border-border text-text-muted hover:text-text'
                }`}
              >
                {f.label} <span className="mono text-text-faint">{count(key)}</span>
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {rows.length > 0 ? (
            <DataTable
              rows={rows}
              onRowClick={(r) => navigate(`/reviewer/cases/${r.case_id}`)}
              columns={[
                { key: 'case_id', header: 'Case ID', render: (r) => <span className="mono text-xs text-text-muted">#{r.case_id.slice(0, 8).toUpperCase()}</span> },
                { key: 'user_email', header: 'User' },
                { key: 'risk', header: 'Risk', render: (r) => <ScoreIndicator score={r.fraud_risk_score} level={r.risk_level} /> },
                { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
                { key: 'created_at', header: 'Created', render: (r) => <span className="mono text-xs">{new Date(r.created_at).toLocaleString()}</span> },
                { key: 'a', header: '', render: () => <span className="text-xs font-medium text-brand">Review →</span> },
              ]}
            />
          ) : (
            <EmptyState title="No cases match this filter" description="Cases appear here as applicants complete verification." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
