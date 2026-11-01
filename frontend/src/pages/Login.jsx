import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { Card } from '../components/Card'
import { Field, Input } from '../components/Form'
import Button from '../components/Button'
import { ErrorBanner } from '../components/Feedback'
import { apiErrorMessage } from '../services/api'

const FEATURES = [
  'Document Intelligence',
  'Face Verification',
  'Liveness Detection',
  'rPPG Physiological Signal',
  'Deepfake Defense',
  'Explainable Risk Engine',
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const data = await login(email, password)
      const dest = location.state?.from?.pathname || (data.role === 'REVIEWER' || data.role === 'ADMIN' ? '/reviewer' : '/dashboard')
      navigate(dest, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Invalid email or password.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto grid min-h-[80vh] max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-2">
      {/* LEFT: product identity */}
      <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
        <span className="inline-block rounded-full border border-brand/30 bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
          Secure AI Identity Platform
        </span>
        <h1 className="mt-4 font-display text-4xl font-semibold leading-tight text-text sm:text-5xl">
          KYC <span className="text-brand">Intelligence</span>
        </h1>
        <p className="mt-2 text-lg text-text-muted">AI-Powered Identity Verification</p>

        <ul className="mt-8 space-y-3">
          {FEATURES.map((f, i) => (
            <motion.li
              key={f}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.1 + i * 0.06 }}
              className="flex items-center gap-2.5 text-sm text-text"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-verified/15 text-verified">✓</span>
              {f}
            </motion.li>
          ))}
        </ul>

        <ScanVisualization />
      </motion.div>

      {/* RIGHT: login card */}
      <motion.div initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
        <Card className="mx-auto max-w-md p-6 illuminate">
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-text">Sign in</h2>
            <p className="mt-1 text-sm text-text-muted">Access your KYC dashboard or the reviewer console.</p>
          </div>
          <form onSubmit={onSubmit} className="space-y-4">
            <ErrorBanner message={error} />
            <Field label="Email">
              <Input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Field label="Password">
              <Input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <Button type="submit" className="w-full" loading={submitting}>
              Sign in
            </Button>
          </form>
        </Card>
        <p className="mt-4 text-center text-sm text-text-muted">
          Don't have an account?{' '}
          <Link to="/register" className="text-brand hover:underline">
            Create one
          </Link>
        </p>
      </motion.div>
    </div>
  )
}

// Subtle, decorative, performant (pure CSS/SVG, no canvas/webgl)
// radar-style security visualization. Respects prefers-reduced-motion
// via the .scan-line class defined in index.css.
function ScanVisualization() {
  return (
    <div className="relative mt-10 hidden h-40 w-40 items-center justify-center sm:flex" aria-hidden="true">
      <div className="absolute inset-0 rounded-full border border-brand/20" />
      <div className="absolute inset-6 rounded-full border border-brand/15" />
      <div className="absolute inset-12 rounded-full border border-brand/10" />
      <div className="absolute inset-0 overflow-hidden rounded-full">
        <div className="scan-line absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand to-transparent" />
      </div>
      <div className="h-2.5 w-2.5 rounded-full bg-brand shadow-[0_0_12px_2px_rgba(56,189,248,0.7)]" />
    </div>
  )
}
