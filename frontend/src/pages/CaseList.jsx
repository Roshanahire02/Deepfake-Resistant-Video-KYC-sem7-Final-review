import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, { apiErrorMessage } from '../services/api'
import PageHeader from '../components/PageHeader'
import { Card, CardContent } from '../components/Card'
import { LoadingSpinner, ErrorState, EmptyState } from '../components/Feedback'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import Button from '../components/Button'

// Shared by "My Cases" (all cases) and "AI Results" (cases that have
// reached a risk decision). Uses the existing GET /api/kyc/list.
export default function CaseList({ resultsOnly = false }) {
  const navigate = useNavigate()
  const [cases, setCases] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/kyc/list')
      .then((res) => setCases(res.data))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load your cases.')))
      .finally(() => setLoading(false))
  }, [])

  const DECIDED = ['RISK_CALCULATED', 'VERIFIED', 'MANUAL_REVIEW', 'FLAGGED', 'REJECTED']
  const rows = cases ? (resultsOnly ? cases.filter((c) => DECIDED.includes(c.status)) : cases) : []

  return (
    <div>
      <PageHeader
        title={resultsOnly ? 'AI Results' : 'My Cases'}
        breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">AI KYC Command Center</span>}
        description={resultsOnly ? 'Cases that have completed AI analysis and received a risk decision.' : 'All of your identity verification cases.'}
        action={<Link to="/new-kyc"><Button>New Verification</Button></Link>}
      />
      {loading && <LoadingSpinner label="Loading cases..." />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && !error && (
        <Card>
          <CardContent>
            {rows.length > 0 ? (
              <DataTable
                rows={rows}
                onRowClick={(r) => navigate(`/cases/${r.id}`)}
                columns={[
                  { key: 'id', header: 'Case ID', render: (r) => <span className="mono text-xs text-text-muted">#{r.id.slice(0, 8).toUpperCase()}</span> },
                  { key: 'created_at', header: 'Created', render: (r) => <span className="mono text-xs">{new Date(r.created_at).toLocaleString()}</span> },
                  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
                  { key: 'a', header: '', render: (r) => <Link to={`/cases/${r.id}`} className="text-xs font-medium text-brand hover:underline" onClick={(e) => e.stopPropagation()}>Open →</Link> },
                ]}
              />
            ) : (
              <EmptyState
                title={resultsOnly ? 'No completed analyses yet' : 'No KYC cases yet'}
                description={resultsOnly ? 'Complete a verification to see AI results here.' : 'Start your first verification to see it here.'}
                action={<Link to="/new-kyc"><Button>New Verification</Button></Link>}
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
