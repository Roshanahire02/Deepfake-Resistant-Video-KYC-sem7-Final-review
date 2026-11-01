import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import api, { apiErrorMessage } from '../services/api'
import PageHeader from '../components/PageHeader'
import { Card, StatCard } from '../components/Card'
import { LoadingSpinner, ErrorState } from '../components/Feedback'
import StatusBadge from '../components/StatusBadge'

// Keyword -> stable anchor id, used by the sidebar's "AI Systems"
// links (see AppShell.jsx). Matched against the real `model` name the
// backend returns, so this never invents a system that doesn't exist.
const ANCHOR_RULES = [
  [['face recognition', 'insightface', 'arcface'], 'face-recognition'],
  [['face detection'], 'face-detection'],
  [['liveness'], 'liveness'],
  [['rppg', 'photoplethysmography'], 'rppg'],
  [['replay'], 'replay-detection'],
  [['deepfake'], 'deepfake'],
  [['risk engine', 'fraud risk'], 'risk-engine'],
  [['ocr'], 'ocr'],
  [['tampering'], 'tampering'],
]

function anchorFor(modelName) {
  const n = modelName.toLowerCase()
  for (const [keywords, id] of ANCHOR_RULES) {
    if (keywords.some((k) => n.includes(k))) return id
  }
  return null
}

// Normalizes the honest backend status string into one of the four
// states the spec calls for, without changing or hiding the real text
// shown below it.
function deriveState(status) {
  const s = (status || '').toUpperCase()
  if (s.includes('NOT INSTALLED') || s.includes('UNAVAILABLE')) return 'UNAVAILABLE'
  if (s.includes('TRAINING REQUIRED')) return 'TRAINING REQUIRED'
  if (s.includes('AVAILABLE') || s.includes('LOADED')) return 'ONLINE'
  return 'DEGRADED'
}

export default function ModelStatus() {
  const location = useLocation()
  const [models, setModels] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get('/system/models')
      .then((res) => setModels(res.data))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load model status.')))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!loading && models && location.hash) {
      const el = document.getElementById(location.hash.slice(1))
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [loading, models, location.hash])

  const counts = models?.reduce(
    (acc, m) => {
      const state = deriveState(m.status)
      acc[state] = (acc[state] || 0) + 1
      return acc
    },
    {}
  )

  return (
    <div>
      <PageHeader
        title="AI Model Control Center"
        description="Live-checked status of every AI/ML component in the verification pipeline -- never shown as ONLINE if the underlying dependency or checkpoint is actually missing."
      />

      {loading && <LoadingSpinner label="Checking models..." />}
      {!loading && error && <ErrorState message={error} />}

      {!loading && models && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Online" value={counts['ONLINE'] || 0} tone="verified" />
            <StatCard label="Training Required" value={counts['TRAINING REQUIRED'] || 0} tone="pending" />
            <StatCard label="Unavailable" value={counts['UNAVAILABLE'] || 0} tone="flagged" />
            <StatCard label="Total Systems" value={models.length} />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {models.map((m) => {
              const state = deriveState(m.status)
              const id = anchorFor(m.model)
              return (
                <Card key={m.model} id={id || undefined} className="scroll-mt-6 p-5" glow>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-text">{m.model}</div>
                      <div className="mt-0.5 text-xs text-text-muted">{m.purpose}</div>
                    </div>
                    <StatusBadge status={state} />
                  </div>
                  <p className="mt-3 text-xs text-text-muted">{m.status}</p>
                  <p className="mt-2 text-[11px] text-text-faint">
                    <span className="uppercase tracking-wide">Evaluation: </span>
                    <span className={m.evaluation?.state === 'NOT_EVALUATED' ? '' : 'mono text-text-muted'}>
                      {m.evaluation?.summary || 'Not evaluated yet'}
                    </span>
                  </p>
                  <dl className="mono mt-3 flex items-center justify-between text-[11px] text-text-faint">
                    <span>{m.version}</span>
                    <span>{m.device}</span>
                  </dl>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
