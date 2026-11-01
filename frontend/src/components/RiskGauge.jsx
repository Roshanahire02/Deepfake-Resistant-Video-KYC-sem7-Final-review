// Circular fraud-risk gauge. `score` (0-100) and `level`
// (LOW/MEDIUM/HIGH -- the exact three bands the backend risk engine
// actually produces, see RiskLevel in app/models/results.py) are
// always passed in from a real risk assessment; this component never
// invents its own thresholds or a 4th band the API doesn't emit.
const LEVEL_META = {
  LOW: { color: '#22c55e', label: 'LOW RISK' },
  MEDIUM: { color: '#f59e0b', label: 'MEDIUM RISK' },
  HIGH: { color: '#ef4444', label: 'HIGH RISK' },
}

export default function RiskGauge({ score, level, size = 220 }) {
  const hasScore = typeof score === 'number' && !Number.isNaN(score)
  const clamped = hasScore ? Math.max(0, Math.min(100, score)) : 0
  const meta = LEVEL_META[level] || { color: '#54637c', label: 'NOT YET ASSESSED' }

  const r = 84
  const circumference = 2 * Math.PI * r
  const offset = circumference * (1 - clamped / 100)

  return (
    <div
      className="flex flex-col items-center"
      role="img"
      aria-label={hasScore ? `Fraud risk score ${Math.round(clamped)} out of 100, ${meta.label}` : 'Fraud risk not yet assessed'}
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox="0 0 200 200" className="-rotate-90">
          <circle cx="100" cy="100" r={r} fill="none" stroke="#141c2a" strokeWidth="14" />
          {hasScore && (
            <circle
              cx="100"
              cy="100"
              r={r}
              fill="none"
              stroke={meta.color}
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              style={{ filter: `drop-shadow(0 0 6px ${meta.color}99)`, transition: 'stroke-dashoffset 700ms ease' }}
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="mono text-5xl font-semibold" style={{ color: meta.color }}>
            {hasScore ? Math.round(clamped) : '—'}
          </div>
          <div className="text-[11px] uppercase tracking-wider text-text-faint">out of 100</div>
        </div>
      </div>
      <div className="mt-3 text-xs font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
        {meta.label}
      </div>
    </div>
  )
}

// Small inline variant for tables / list rows where the full gauge is too heavy.
export function ScoreIndicator({ score, level }) {
  const meta = LEVEL_META[level] || { color: '#54637c', label: '—' }
  const hasScore = typeof score === 'number' && !Number.isNaN(score)
  return (
    <span className="inline-flex items-center gap-2">
      <span className="mono text-sm font-semibold" style={{ color: meta.color }}>
        {hasScore ? Math.round(score) : '—'}
      </span>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-border-soft">
        <span className="block h-full rounded-full" style={{ width: `${hasScore ? score : 0}%`, background: meta.color }} />
      </span>
    </span>
  )
}
