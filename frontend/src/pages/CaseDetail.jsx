import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import api, { apiErrorMessage, downloadReport } from '../services/api'
import PageHeader from '../components/PageHeader'
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card'
import { LoadingSpinner, ErrorState, ErrorBanner } from '../components/Feedback'
import StatusBadge from '../components/StatusBadge'
import RiskGauge from '../components/RiskGauge'
import Button from '../components/Button'

const VERDICT_META = {
  VERIFIED: { label: 'CASE VERIFIED', color: 'text-verified', ring: 'border-verified/30 bg-verified/5' },
  MANUAL_REVIEW: { label: 'UNDER REVIEW', color: 'text-review', ring: 'border-review/30 bg-review/5' },
  FLAGGED: { label: 'CASE FLAGGED', color: 'text-flagged', ring: 'border-flagged/30 bg-flagged/5' },
  REJECTED: { label: 'CASE REJECTED', color: 'text-flagged', ring: 'border-flagged/30 bg-flagged/5' },
}

function VerdictBanner({ status }) {
  const meta = VERDICT_META[status] || { label: status?.replace(/_/g, ' ') || 'IN PROGRESS', color: 'text-text-muted', ring: 'border-border bg-surface' }
  return (
    <div className={`mb-6 rounded-xl border px-6 py-5 ${meta.ring}`}>
      <div className={`font-display text-2xl font-semibold tracking-wide ${meta.color}`}>{meta.label}</div>
    </div>
  )
}

function MeterBar({ value, color = 'bg-brand' }) {
  const pct = Math.max(0, Math.min(100, (value ?? 0) * 100))
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-border-soft">
      <motion.div
        className={`h-full rounded-full ${color}`}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  )
}

// Renders one AI system's result as a card. Only ever shows values the
// backend actually returned -- `rows` entries with a null value render
// as an em dash rather than being hidden or guessed at. `meter` (0-1)
// optionally draws a progress bar under the status, honestly derived
// from a real backend field (never fabricated).
function ResultCard({ title, data, statusKey = 'status', rows = [], meter, meterColor }) {
  if (!data) {
    return (
      <Card className="p-5">
        <div className="text-sm font-semibold text-text">{title}</div>
        <div className="mt-3 text-xs text-text-faint">Not yet available for this case.</div>
      </Card>
    )
  }
  return (
    <Card className="p-5" glow>
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-text">{title}</div>
        <StatusBadge status={data[statusKey]} />
      </div>
      {meter != null && (
        <div className="mt-3">
          <MeterBar value={meter} color={meterColor} />
        </div>
      )}
      <dl className="mt-3 space-y-1.5 text-xs">
        {rows.map(([label, key, fmt]) => (
          <div key={key} className="flex items-center justify-between">
            <dt className="text-text-faint">{label}</dt>
            <dd className="mono text-text">
              {data[key] === null || data[key] === undefined ? '—' : fmt ? fmt(data[key]) : String(data[key])}
            </dd>
          </div>
        ))}
      </dl>
      {data.message && <p className="mt-3 text-xs text-text-muted">{data.message}</p>}
    </Card>
  )
}

// rPPG's raw waveform is never stored (privacy design -- only derived
// metrics are persisted, see RPPGResult in app/models/results.py), so
// this is NOT a fabricated pulse waveform. It's an honest bar-meter
// visualization built only from the three real signal-quality metrics
// the backend actually returned.
function RppgSignalMeters({ rppg }) {
  if (!rppg || rppg.status !== 'AVAILABLE') return null
  const metrics = [
    ['Signal Quality', rppg.signal_quality],
    ['Periodicity', rppg.periodicity_score],
    ['Temporal Consistency', rppg.temporal_consistency],
  ]
  return (
    <div className="mt-3 space-y-2">
      {metrics.map(([label, value]) => (
        <div key={label}>
          <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wide text-text-faint">
            <span>{label}</span>
            <span className="mono">{value != null ? `${Math.round(value * 100)}%` : '—'}</span>
          </div>
          <MeterBar value={value} color="bg-brand-2" />
        </div>
      ))}
    </div>
  )
}

// Face match: the backend returns only scores, never image bytes, so
// per spec we show honest placeholders (never a fabricated photo) with
// the real similarity score connecting them.
function FaceMatchVisual({ face }) {
  if (!face) return null
  const matched = (face.match_status || '').toUpperCase().includes('MATCH') && !(face.match_status || '').toUpperCase().includes('NOT')
  const hasScore = typeof face.similarity_score === 'number'
  return (
    <div className="mt-3 flex items-center justify-center gap-4">
      <FaceSlot label="Document" />
      <div className="flex flex-col items-center">
        <div className={`mono text-lg font-semibold ${matched ? 'text-verified' : 'text-flagged'}`}>
          {hasScore ? `${Math.round(face.similarity_score * 100)}%` : '—'}
        </div>
        <div className="h-px w-10 bg-gradient-to-r from-brand/60 to-brand/10" />
      </div>
      <FaceSlot label="Live" />
    </div>
  )
}
function FaceSlot({ label }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-border-soft bg-surface-raised text-text-faint">
        <svg width="24" height="24" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <circle cx="9" cy="6" r="3" stroke="currentColor" strokeWidth="1.3" />
          <path d="M3 16c1-3.3 3.6-5 6-5s5 1.7 6 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      </div>
      <span className="text-[10px] uppercase tracking-wide text-text-faint">{label}</span>
    </div>
  )
}

const TABS = [
  ['overview', 'Overview'], ['document', 'Document'], ['biometrics', 'Biometrics'], ['liveness', 'Liveness'],
  ['rppg', 'rPPG'], ['replay', 'Replay'], ['deepfake', 'Deepfake'], ['risk', 'Risk'],
  ['explain', 'Explainability'], ['audit', 'Audit'],
]

export default function CaseDetail() {
  const { caseId } = useParams()
  const [caseData, setCaseData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reportError, setReportError] = useState('')
  const [tab, setTab] = useState('overview')

  useEffect(() => {
    let mounted = true
    api
      .get(`/kyc/${caseId}`)
      .then((res) => mounted && setCaseData(res.data))
      .catch((err) => mounted && setError(apiErrorMessage(err, 'Could not load this case.')))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [caseId])

  if (loading) return <LoadingSpinner label="Loading case..." />
  if (error) return <ErrorState message={error} />
  if (!caseData) return null

  const risk = caseData.risk
  const d = caseData

  // Each system's card is built once and reused by Overview and its own tab.
  const documentCard = (
    <ResultCard
      title="Document Verification"
      data={d.document}
      statusKey="tampering_flag"
      meter={d.document ? (d.document.authenticity_score ?? 0) / 100 : null}
      meterColor="bg-brand"
      rows={[
        ['Extracted name', 'extracted_name'],
        ['Extracted DOB', 'extracted_dob'],
        ['Document number', 'extracted_doc_number'],
        ['Authenticity score', 'authenticity_score', (v) => `${Math.round(v)}%`],
        ['Tampering probability', 'tampering_probability', (v) => `${Math.round(v * 100)}%`],
      ]}
    />
  )
  const faceCard = (
    <Card className="p-5" glow>
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-text">Face Verification</div>
        {d.face && <StatusBadge status={d.face.match_status} />}
      </div>
      {d.face ? (
        <>
          <FaceMatchVisual face={d.face} />
          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <dt className="text-text-faint">Face quality</dt>
              <dd className="mono text-text">{d.face.face_quality_score != null ? `${Math.round(d.face.face_quality_score * 100)}%` : '—'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-text-faint">Threshold</dt>
              <dd className="mono text-text">{d.face.threshold_used != null ? `${Math.round(d.face.threshold_used * 100)}%` : '—'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-text-faint">Multiple faces</dt>
              <dd className="mono text-text">{d.face.multiple_faces_detected == null ? '—' : d.face.multiple_faces_detected ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
        </>
      ) : (
        <div className="mt-3 text-xs text-text-faint">Not yet available for this case.</div>
      )}
    </Card>
  )
  const livenessCard = (
    <ResultCard
      title="Liveness Detection"
      data={d.liveness ? { ...d.liveness, status: d.liveness.passed ? 'PASSED' : 'FAILED' } : null}
      meter={d.liveness ? d.liveness.confidence : null}
      meterColor="bg-review"
      rows={[
        ['Challenge', 'challenge_type'],
        ['Blink count', 'blink_count'],
        ['Motion score', 'motion_score', (v) => v.toFixed(3)],
        ['Confidence', 'confidence', (v) => `${Math.round(v * 100)}%`],
      ]}
    />
  )
  const rppgCard = (
    <Card className="p-5" glow>
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-text">rPPG -- Physiological Signal</div>
        {d.rppg && <StatusBadge status={d.rppg.status} />}
      </div>
      {d.rppg ? (
        <>
          <RppgSignalMeters rppg={d.rppg} />
          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <dt className="text-text-faint">Heart rate (estimate)</dt>
              <dd className="mono text-text">{d.rppg.heart_rate_bpm != null ? `${d.rppg.heart_rate_bpm} BPM` : '—'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-text-faint">Usable frames</dt>
              <dd className="mono text-text">{d.rppg.usable_frames ?? '—'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-text-faint">Method</dt>
              <dd className="mono text-text">{d.rppg.method_version ?? '—'}</dd>
            </div>
          </dl>
          {d.rppg.message && <p className="mt-3 text-xs text-text-muted">{d.rppg.message}</p>}
          <p className="mt-3 text-[11px] text-text-faint">A camera-based signal estimate used as one liveness signal -- not a medical measurement.</p>
        </>
      ) : (
        <div className="mt-3 text-xs text-text-faint">Not yet available for this case.</div>
      )}
    </Card>
  )
  const replayCard = (
    <ResultCard
      title="Replay Defense"
      data={d.replay}
      meter={d.replay ? d.replay.replay_probability : null}
      meterColor="bg-flagged"
      rows={[['Replay probability', 'replay_probability', (v) => `${Math.round(v * 100)}%`]]}
    />
  )
  const deepfakeCard = (
    <ResultCard
      title="Deepfake Forensics"
      data={d.deepfake}
      meter={d.deepfake ? d.deepfake.deepfake_probability : null}
      meterColor="bg-pending"
      rows={[
        ['Probability', 'deepfake_probability', (v) => `${Math.round(v * 100)}%`],
        ['Frames analyzed', 'frames_analyzed'],
        ['Model version', 'model_version'],
      ]}
    />
  )

  const contributions = risk?.feature_contributions && Object.keys(risk.feature_contributions).length > 0 ? risk.feature_contributions : null
  const gauge = risk ? (
    <div className="grid gap-8 md:grid-cols-[auto_1fr] md:items-center">
      <RiskGauge score={risk.fraud_risk_score} level={risk.risk_level} />
      <div>
        <StatusBadge status={risk.decision} />
        <p className="mt-3 text-sm text-text-muted">{risk.explanation_text}</p>
      </div>
    </div>
  ) : (
    <p className="text-sm text-text-muted">Fraud risk has not been calculated yet -- complete document analysis and Video KYC first.</p>
  )
  const shap = contributions ? (
    <div>
      <div className="mb-3 text-xs font-medium uppercase tracking-wide text-text-faint">Why did AI flag this case? (SHAP contributions)</div>
      <div className="space-y-2.5">
        {Object.entries(contributions).map(([name, value]) => {
          const max = Math.max(...Object.values(contributions).map(Math.abs), 0.001)
          const width = (Math.abs(value) / max) * 100
          const positive = value >= 0
          return (
            <div key={name}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-text-muted">{name.replace(/_/g, ' ')}</span>
                <span className={`mono ${positive ? 'text-flagged' : 'text-verified'}`}>{positive ? '+' : ''}{value.toFixed(3)}</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-border-soft">
                <motion.div className={`h-full rounded-full ${positive ? 'bg-flagged' : 'bg-verified'}`} initial={{ width: 0 }} animate={{ width: `${width}%` }} transition={{ duration: 0.5 }} />
              </div>
            </div>
          )
        })}
      </div>
      <p className="mt-2 text-[11px] text-text-faint">Positive values pushed risk up; negative values pushed it down. Computed by SHAP from the trained risk model.</p>
    </div>
  ) : (
    <p className="text-sm text-text-muted">No SHAP contributions are available for this case.</p>
  )

  const panels = {
    overview: (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documentCard}{faceCard}{livenessCard}{rppgCard}{replayCard}{deepfakeCard}
        </div>
        <Card glow>
          <CardHeader><CardTitle subtitle="Combines every signal into a single explainable AI risk decision.">AI Risk Intelligence</CardTitle></CardHeader>
          <CardContent>{gauge}</CardContent>
        </Card>
      </div>
    ),
    document: <div className="max-w-xl">{documentCard}</div>,
    biometrics: <div className="max-w-xl">{faceCard}</div>,
    liveness: <div className="max-w-xl">{livenessCard}</div>,
    rppg: <div className="max-w-xl">{rppgCard}</div>,
    replay: <div className="max-w-xl">{replayCard}</div>,
    deepfake: <div className="max-w-xl">{deepfakeCard}</div>,
    risk: (
      <Card glow>
        <CardHeader><CardTitle>AI Risk Intelligence</CardTitle></CardHeader>
        <CardContent>{gauge}</CardContent>
      </Card>
    ),
    explain: (
      <Card>
        <CardHeader><CardTitle subtitle="Real SHAP values from the risk model -- nothing is estimated here.">Explainability</CardTitle></CardHeader>
        <CardContent>{shap}</CardContent>
      </Card>
    ),
    audit: (
      <Card>
        <CardHeader><CardTitle>Audit</CardTitle></CardHeader>
        <CardContent>
          <dl className="space-y-2 text-xs">
            {[
              ['Case ID', d.id], ['Status', d.status?.replace(/_/g, ' ')], ['Created', new Date(d.created_at).toLocaleString()],
              ['Risk model', risk?.model_version], ['Deepfake model', d.deepfake?.model_version], ['rPPG method', d.rppg?.method_version],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-4 border-b border-border-soft pb-2 last:border-0">
                <dt className="text-text-faint">{k}</dt><dd className="mono break-all text-right text-text">{v || '—'}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-[11px] text-text-faint">Raw video is never stored; only the derived results above are retained.</p>
        </CardContent>
      </Card>
    ),
  }

  return (
    <div>
      <PageHeader
        title={`CASE #${d.id.slice(0, 8).toUpperCase()}`}
        breadcrumb={<Link to="/dashboard" className="hover:text-text">Dashboard</Link>}
        description={<span className="mono text-xs">{d.id}</span>}
        action={<StatusBadge status={d.status} />}
      />
      <VerdictBanner status={d.status} />

      <div role="tablist" aria-label="Case analysis sections" className="mb-5 flex flex-wrap gap-1.5 border-b border-border-soft pb-3">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            id={`tab-${key}`}
            aria-selected={tab === key}
            aria-controls={`panel-${key}`}
            onClick={() => setTab(key)}
            className={`rounded-lg border px-3 py-1.5 text-xs transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand ${
              tab === key ? 'border-brand bg-brand-soft text-brand' : 'border-border text-text-muted hover:text-text'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          role="tabpanel"
          id={`panel-${tab}`}
          aria-labelledby={`tab-${tab}`}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          {panels[tab]}
        </motion.div>
      </AnimatePresence>

      <div className="mt-6"><ErrorBanner message={reportError} /></div>
      <div className="mt-3 flex gap-3">
        <Link to="/dashboard"><Button variant="outline">Back to dashboard</Button></Link>
        {risk && (
          <Button variant="secondary" onClick={() => { setReportError(''); downloadReport(d.id).catch((e) => setReportError(apiErrorMessage(e, 'Could not generate this report.'))) }}>
            Download Report
          </Button>
        )}
      </div>
    </div>
  )
}
