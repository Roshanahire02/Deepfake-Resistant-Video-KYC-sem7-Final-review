import { Link } from 'react-router-dom'
import { Card } from '../components/Card'

const STAGES = [
  'Document OCR + tampering analysis',
  'Liveness challenge (blink / head-turn)',
  'Deepfake probability scoring',
  'Replay-attack detection',
  'Face-to-document matching',
  'Explainable fraud risk score',
]

export default function Landing() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
      <div className="grid gap-12 md:grid-cols-2 md:items-center">
        <div>
          <span className="inline-block rounded-full border border-brand/30 bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
            B.Tech academic prototype
          </span>
          <h1 className="mt-4 text-4xl font-semibold leading-tight text-text sm:text-5xl">
            Deepfake-resistant <span className="text-brand">Video KYC</span> verification
          </h1>
          <p className="mt-4 text-text-muted">
            Combines document forensics, biometric matching, liveness detection, deepfake and
            replay-attack detection into one explainable fraud-risk pipeline. Every score you see is
            computed from a real model or an explicitly labeled rule-based baseline — never fabricated.
          </p>
          <div className="mt-6 flex gap-3">
            <Link to="/register" className="rounded-lg bg-brand px-5 py-3 text-sm font-medium text-ink hover:brightness-110">
              Start a verification
            </Link>
            <Link to="/login" className="rounded-lg border border-border px-5 py-3 text-sm font-medium text-text hover:border-brand/50">
              Sign in
            </Link>
          </div>
        </div>

        <Card className="p-6">
          <div className="text-xs font-medium uppercase tracking-wide text-text-faint">Verification pipeline</div>
          <ol className="mt-4 space-y-3">
            {STAGES.map((s, i) => (
              <li key={s} className="flex items-center gap-3 text-sm text-text">
                <span className="mono flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-xs text-text-muted">
                  {i + 1}
                </span>
                {s}
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  )
}
