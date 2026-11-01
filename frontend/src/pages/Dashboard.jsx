import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import api, { apiErrorMessage } from '../services/api'
import PageHeader from '../components/PageHeader'
import { StatCard, Card, CardHeader, CardTitle, CardContent } from '../components/Card'
import Button from '../components/Button'
import { LoadingSpinner, ErrorState, EmptyState } from '../components/Feedback'
import DataTable from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'

const PIPELINE_STAGES = ['Document', 'Face', 'Liveness', 'rPPG', 'Replay', 'Deepfake', 'Risk']

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [cases, setCases] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const [summaryRes, listRes] = await Promise.all([
          api.get('/kyc/dashboard/summary'),
          api.get('/kyc/list'),
        ])
        if (!mounted) return
        setSummary(summaryRes.data)
        setCases(listRes.data)
      } catch (err) {
        if (mounted) setError(apiErrorMessage(err, 'Could not load your dashboard.'))
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div>
      <PageHeader
        title={`${greeting()}, ${user?.full_name?.split(' ')[0] || ''}`}
        breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">AI KYC Command Center</span>}
        description="Overview of your identity verification cases."
        action={
          <Link to="/new-kyc">
            <Button>New Verification</Button>
          </Link>
        }
      />

      {loading && <LoadingSpinner label="Loading dashboard..." />}
      {!loading && error && <ErrorState message={error} />}

      {!loading && !error && summary && (
        <>
          <motion.div
            className="grid grid-cols-2 gap-4 sm:grid-cols-4"
            initial="hidden"
            animate="show"
            variants={{ show: { transition: { staggerChildren: 0.06 } } }}
          >
            {[
              { label: 'Total Cases', value: summary.total_cases, tone: 'neutral' },
              { label: 'Verified', value: summary.verified, tone: 'verified' },
              { label: 'Pending', value: summary.pending, tone: 'pending' },
              { label: 'Flagged', value: summary.flagged, tone: 'flagged' },
            ].map((kpi) => (
              <motion.div key={kpi.label} variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}>
                <StatCard label={kpi.label} value={kpi.value} tone={kpi.tone} />
              </motion.div>
            ))}
          </motion.div>

          <Card className="mt-6 p-5">
            <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-faint">
              AI Verification Pipeline
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={stage} className="flex items-center gap-2">
                  <span className="rounded-lg border border-border-soft bg-surface-raised px-3 py-1.5 text-xs font-medium text-text-muted">
                    {stage}
                  </span>
                  {i < PIPELINE_STAGES.length - 1 && <span className="text-text-faint">→</span>}
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-text-faint">
              Every verification runs through this pipeline -- see{' '}
              <Link to="/models" className="text-brand hover:underline">
                Model Status
              </Link>{' '}
              for the live availability of each stage.
            </p>
          </Card>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Recent Cases</CardTitle>
            </CardHeader>
            <CardContent>
              {cases && cases.length > 0 ? (
                <DataTable
                  columns={[
                    { key: 'id', header: 'Case ID', render: (r) => <span className="mono text-xs text-text-muted">{r.id.slice(0, 8)}</span> },
                    { key: 'created_at', header: 'Created', render: (r) => new Date(r.created_at).toLocaleString() },
                    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
                    {
                      key: 'action',
                      header: '',
                      render: (r) => (
                        <Link to={`/cases/${r.id}`} className="text-xs font-medium text-brand hover:underline">
                          View →
                        </Link>
                      ),
                    },
                  ]}
                  rows={cases}
                />
              ) : (
                <EmptyState
                  title="No KYC cases yet"
                  description="Start your first verification to see it here."
                  action={
                    <Link to="/new-kyc">
                      <Button>New Verification</Button>
                    </Link>
                  }
                />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
