import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { apiErrorMessage, downloadReport } from '../../services/api'
import PageHeader from '../../components/PageHeader'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card'
import { LoadingSpinner, ErrorState, ErrorBanner } from '../../components/Feedback'
import StatusBadge from '../../components/StatusBadge'
import RiskGauge from '../../components/RiskGauge'
import Button from '../../components/Button'

const pct = (v) => (v == null ? '—' : `${Math.round(v * 100)}%`)

function Evidence({ title, status, rows }) {
  return (
    <Card className="p-4" glow>
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-text">{title}</div>
        {status ? <StatusBadge status={status} /> : <span className="text-xs text-text-faint">No data</span>}
      </div>
      {status && (
        <dl className="mt-3 space-y-1.5 text-xs">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-center justify-between gap-3">
              <dt className="text-text-faint">{label}</dt>
              <dd className="mono text-right text-text">{value == null || value === '' ? '—' : String(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  )
}

export default function ReviewerCaseDetail() {
  const { caseId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(null)
  const [actionError, setActionError] = useState('')
  const [actionOk, setActionOk] = useState('')

  const load = useCallback(() => {
    return api.get(`/reviewer/cases/${caseId}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load this case.')))
      .finally(() => setLoading(false))
  }, [caseId])

  useEffect(() => { load() }, [load])

  async function decide(action) {
    setActionError('')
    setActionOk('')
    setSubmitting(action)
    try {
      const res = await api.put(`/reviewer/cases/${caseId}/decision`, { action, notes: notes || null })
      setActionOk(`Decision recorded: case is now ${res.data.new_status.replace(/_/g, ' ')}.`)
      setNotes('')
      await load()
    } catch (err) {
      setActionError(apiErrorMessage(err, 'Could not record the decision.'))
    } finally {
      setSubmitting(null)
    }
  }

  if (loading) return <LoadingSpinner label="Loading case..." />
  if (error) return <ErrorState message={error} />
  if (!data) return null

  const { case: c, document: doc, face, liveness, rppg, replay, deepfake, risk, reviewer_actions: actions } = data

  return (
    <div>
      <PageHeader
        title={`CASE #${c.id.slice(0, 8).toUpperCase()}`}
        breadcrumb={<Link to="/reviewer" className="hover:text-text">Reviewer Console</Link>}
        description={<span className="mono text-xs">{c.id}</span>}
        action={<StatusBadge status={c.status} />}
      />

      <div className="grid gap-5 lg:grid-cols-[260px_1fr_320px]">
        {/* LEFT: case information */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Case Information</CardTitle></CardHeader>
            <CardContent>
              <dl className="space-y-2 text-xs">
                <div><dt className="text-text-faint">Applicant</dt><dd className="mt-0.5 break-all text-text">{c.user_email}</dd></div>
                <div><dt className="text-text-faint">Created</dt><dd className="mono mt-0.5 text-text">{new Date(c.created_at).toLocaleString()}</dd></div>
              </dl>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Audit Trail</CardTitle></CardHeader>
            <CardContent>
              {actions && actions.length > 0 ? (
                <ul className="space-y-3 text-xs">
                  {actions.map((a) => (
                    <li key={a.id} className="border-l border-brand/30 pl-3">
                      <StatusBadge status={a.action} />
                      <div className="mono mt-1 text-[11px] text-text-faint">{new Date(a.decided_at).toLocaleString()}</div>
                      {a.notes && <p className="mt-1 text-text-muted">{a.notes}</p>}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-text-faint">No reviewer decisions recorded yet.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* CENTER: evidence */}
        <div className="grid content-start gap-4 sm:grid-cols-2">
          <Evidence
            title="Document"
            status={doc ? (doc.tampering_flag ? 'FLAGGED' : doc.authenticity_score == null ? 'UNAVAILABLE' : 'VERIFIED') : null}
            rows={doc ? [
              ['Name (OCR)', doc.extracted_name],
              ['Authenticity', doc.authenticity_score != null ? `${Math.round(doc.authenticity_score)}%` : null],
              ['Tampering prob.', pct(doc.tampering_probability)],
            ] : []}
          />
          <Evidence
            title="Face Verification"
            status={face?.match_status}
            rows={face ? [['Similarity', pct(face.similarity_score)], ['Face quality', pct(face.face_quality_score)], ['Threshold', pct(face.threshold_used)]] : []}
          />
          <Evidence
            title="Liveness"
            status={liveness ? (liveness.passed ? 'PASSED' : 'FAILED') : null}
            rows={liveness ? [['Challenge', liveness.challenge_type], ['Blinks', liveness.blink_count], ['Confidence', pct(liveness.confidence)]] : []}
          />
          <Evidence
            title="rPPG Signal"
            status={rppg?.status}
            rows={rppg ? [
              ['Heart rate', rppg.heart_rate_bpm != null ? `${rppg.heart_rate_bpm} BPM` : null],
              ['Signal quality', pct(rppg.signal_quality)],
              ['Consistency', pct(rppg.temporal_consistency)],
              ['Usable frames', rppg.usable_frames],
            ] : []}
          />
          <Evidence title="Replay Defense" status={replay?.status} rows={replay ? [['Replay prob.', pct(replay.replay_probability)]] : []} />
          <Evidence
            title="Deepfake Forensics"
            status={deepfake?.status}
            rows={deepfake ? [['Probability', pct(deepfake.deepfake_probability)], ['Frames', deepfake.frames_analyzed], ['Model', deepfake.model_version]] : []}
          />
        </div>

        {/* RIGHT: AI decision + reviewer actions */}
        <div className="space-y-4">
          <Card glow>
            <CardHeader><CardTitle>AI Recommendation</CardTitle></CardHeader>
            <CardContent>
              {risk ? (
                <>
                  <RiskGauge score={risk.fraud_risk_score} level={risk.risk_level} size={170} />
                  <div className="mt-3 flex justify-center"><StatusBadge status={risk.decision} /></div>
                  <p className="mt-3 text-xs text-text-muted">{risk.explanation_text}</p>
                  <p className="mono mt-2 text-[10px] text-text-faint">{risk.model_version}</p>
                </>
              ) : (
                <p className="text-xs text-text-faint">Risk has not been calculated for this case.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Reviewer Decision</CardTitle></CardHeader>
            <CardContent>
              <ErrorBanner message={actionError} />
              {actionOk && <div role="status" className="mb-3 rounded-lg border border-verified/30 bg-verified/10 px-4 py-3 text-sm text-verified">{actionOk}</div>}
              <label className="block text-xs font-medium text-text-muted" htmlFor="reviewer-notes">Reviewer notes</label>
              <textarea
                id="reviewer-notes"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-border bg-ink px-3 py-2 text-sm text-text placeholder:text-text-faint focus:border-brand focus:outline-none"
                placeholder="Optional notes for the audit trail"
              />
              <div className="mt-3 grid gap-2">
                <Button variant="success" loading={submitting === 'APPROVE'} disabled={!!submitting} onClick={() => decide('APPROVE')}>Approve</Button>
                <Button variant="danger" loading={submitting === 'REJECT'} disabled={!!submitting} onClick={() => decide('REJECT')}>Reject</Button>
                <Button variant="outline" loading={submitting === 'MANUAL_REVIEW'} disabled={!!submitting} onClick={() => decide('MANUAL_REVIEW')}>Send for manual review</Button>
                {risk && <Button variant="ghost" size="sm" onClick={() => downloadReport(c.id).catch((e) => setActionError(apiErrorMessage(e, 'Could not generate this report.')))}>Download report</Button>}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
