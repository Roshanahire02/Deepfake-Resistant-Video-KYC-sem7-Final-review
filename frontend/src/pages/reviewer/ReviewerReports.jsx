import { useEffect, useState } from 'react'
import api, { apiErrorMessage, downloadReport } from '../../services/api'
import PageHeader from '../../components/PageHeader'
import { Card, CardContent } from '../../components/Card'
import { LoadingSpinner, ErrorState, EmptyState, ErrorBanner } from '../../components/Feedback'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import Button from '../../components/Button'

export default function ReviewerReports() {
  const [cases, setCases] = useState(null)
  const [error, setError] = useState('')
  const [dlError, setDlError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)

  useEffect(() => {
    api.get('/reviewer/cases')
      .then((res) => setCases(res.data.filter((c) => c.fraud_risk_score != null).map((c) => ({ ...c, id: c.case_id }))))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load reports.')))
      .finally(() => setLoading(false))
  }, [])

  async function handleDownload(id) {
    setDlError('')
    setBusyId(id)
    try {
      await downloadReport(id)
    } catch (err) {
      setDlError(apiErrorMessage(err, 'Could not generate this report.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <PageHeader title="Reports" breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">Reviewer Console</span>} description="Verification reports for every case with a completed risk assessment." />
      {loading && <LoadingSpinner label="Loading reports..." />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && !error && (
        <Card>
          <CardContent>
            <ErrorBanner message={dlError} />
            {cases && cases.length > 0 ? (
              <DataTable
                rows={cases}
                columns={[
                  { key: 'case_id', header: 'Case ID', render: (r) => <span className="mono text-xs text-text-muted">#{r.case_id.slice(0, 8).toUpperCase()}</span> },
                  { key: 'user_email', header: 'User' },
                  { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
                  { key: 'a', header: '', render: (r) => <Button size="sm" variant="outline" loading={busyId === r.case_id} onClick={() => handleDownload(r.case_id)}>Download Report</Button> },
                ]}
              />
            ) : (
              <EmptyState title="No reports yet" description="Reports become available once a case has a completed risk assessment." />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
