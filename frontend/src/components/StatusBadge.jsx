// Generic status pill used everywhere a backend status string is shown
// (case status, document/liveness/deepfake/replay/reviewer-action
// status). Purely a presentation mapping -- never invents a status,
// only colors/labels the one the API returned.
const TONE_STYLES = {
  verified: 'bg-verified/10 text-verified border-verified/30',
  pending: 'bg-pending/10 text-pending border-pending/30',
  review: 'bg-review/10 text-review border-review/30',
  flagged: 'bg-flagged/10 text-flagged border-flagged/30',
  neutral: 'bg-white/5 text-text-muted border-border',
}

// Matching is on WORD STARTS of the normalized status (underscores -> spaces),
// never raw substrings: a substring match would read "NOT MATCHED" as
// MATCHED (green) and "UNAVAILABLE" as AVAILABLE (green). Negated phrases are
// checked first, then the "unknown/unavailable" family, then the rest -- so
// an unavailable or untrained check can never display as a success.
const RULES = [
  [['NOT MATCHED', 'NO MATCH', 'MISMATCH'], 'flagged'],
  [['NOT DETECTED'], 'verified'],
  [['UNAVAILABLE', 'TRAINING REQUIRED', 'DEPENDENCY', 'NOT EVALUATED', 'NOT INSTALLED', 'INSUFFICIENT', 'PENDING', 'IN PROGRESS', 'NO FACE'], 'pending'],
  [['FLAGGED', 'REJECT', 'FAIL', 'HIGH', 'DETECTED', 'ERROR', 'CRITICAL'], 'flagged'],
  [['MANUAL REVIEW', 'MEDIUM', 'PROCESSING', 'ANALYZING', 'DEGRADED', 'SUSPECTED'], 'review'],
  [['VERIFIED', 'APPROVE', 'PASSED', 'MATCHED', 'LOW', 'DONE', 'COMPLETE', 'ONLINE', 'AVAILABLE'], 'verified'],
]

function toneFor(status) {
  if (!status) return 'neutral'
  const s = String(status).toUpperCase().replace(/_/g, ' ')
  for (const [keywords, tone] of RULES) {
    if (keywords.some((k) => new RegExp(`\\b${k}`).test(s))) return tone
  }
  return 'neutral'
}

const DOT_COLOR = {
  verified: 'text-verified',
  flagged: 'text-flagged',
  review: 'text-review',
  pending: 'text-pending',
  neutral: 'text-text-faint',
}

// 'live' statuses pulse to read as actively-monitored, not just inert text.
const LIVE_TONES = new Set(['review'])

export default function StatusBadge({ status, label, showIcon = true }) {
  const tone = toneFor(status)
  return (
    <span
      role="status"
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium mono tracking-wide ${TONE_STYLES[tone]}`}
    >
      {showIcon && (
        <span
          aria-hidden="true"
          className={`h-1.5 w-1.5 rounded-full bg-current ${DOT_COLOR[tone]} ${LIVE_TONES.has(tone) ? 'pulse-dot' : ''}`}
        />
      )}
      {(label || status || 'UNKNOWN').toString().replace(/_/g, ' ')}
    </span>
  )
}
