import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import StatusBadge from '../components/StatusBadge'
import RiskGauge, { ScoreIndicator } from '../components/RiskGauge'
import ProtectedRoute from '../components/ProtectedRoute'

// ProtectedRoute reads auth state from context; mock just that hook.
const mockAuth = vi.hoisted(() => ({ value: {} }))
vi.mock('../context/AuthContext', () => ({ useAuth: () => mockAuth.value }))

describe('StatusBadge', () => {
  it('shows backend status text with underscores humanized', () => {
    render(<StatusBadge status="MANUAL_REVIEW" />)
    expect(screen.getByRole('status')).toHaveTextContent('MANUAL REVIEW')
  })

  it.each([
    ['VERIFIED', 'text-verified'],
    ['FLAGGED', 'text-flagged'],
    ['MANUAL_REVIEW', 'text-review'],
    ['TRAINING_REQUIRED', 'text-pending'],
    ['INSUFFICIENT_SIGNAL', 'text-pending'],
    ['NOT_MATCHED', 'text-flagged'],
    ['MATCHED', 'text-verified'],
    ['UNAVAILABLE', 'text-pending'],
    ['DEPENDENCY_UNAVAILABLE', 'text-pending'],
    ['NOT_DETECTED', 'text-verified'],
    ['DETECTED', 'text-flagged'],
    ['SUSPECTED', 'text-review'],
    ['AVAILABLE', 'text-verified'],
    ['APPROVE', 'text-verified'],
    ['REJECT', 'text-flagged'],
    ['ONLINE', 'text-verified'],
    ['NO_FACE_FRAMES', 'text-pending'],
  ])('%s gets the %s tone -- and never reads as verified unless it is', (status, cls) => {
    render(<StatusBadge status={status} />)
    expect(screen.getByRole('status').className).toContain(cls)
  })

  it.each(['TRAINING_REQUIRED', 'UNAVAILABLE', 'INSUFFICIENT_SIGNAL', 'NOT_MATCHED', 'DEPENDENCY_UNAVAILABLE'])(
    'never shows %s as verified (green)',
    (status) => {
      render(<StatusBadge status={status} />)
      expect(screen.getByRole('status').className).not.toContain('text-verified')
    }
  )
})

describe('RiskGauge', () => {
  it('renders the real score and level', () => {
    render(<RiskGauge score={55.4} level="MEDIUM" />)
    expect(screen.getByText('55')).toBeInTheDocument()
    expect(screen.getByText('MEDIUM RISK')).toBeInTheDocument()
  })

  it('handles a missing score without inventing one', () => {
    render(<RiskGauge score={null} level={null} />)
    expect(screen.getByText('NOT YET ASSESSED')).toBeInTheDocument()
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', 'Fraud risk not yet assessed')
  })

  it('ScoreIndicator shows a dash for null', () => {
    render(<ScoreIndicator score={null} level={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})

describe('ProtectedRoute', () => {
  const renderAt = (path = '/secret', allowedRoles) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/dashboard" element={<div>user home</div>} />
          <Route path="/reviewer" element={<div>reviewer home</div>} />
          <Route path="/secret" element={<ProtectedRoute allowedRoles={allowedRoles}><div>secret content</div></ProtectedRoute>} />
        </Routes>
      </MemoryRouter>
    )

  it('redirects unauthenticated visitors to /login', () => {
    mockAuth.value = { isAuthenticated: false, loading: false, user: null }
    renderAt()
    expect(screen.getByText('login page')).toBeInTheDocument()
  })

  it('lets an allowed role through', () => {
    mockAuth.value = { isAuthenticated: true, loading: false, user: { role: 'REVIEWER' } }
    renderAt('/secret', ['REVIEWER'])
    expect(screen.getByText('secret content')).toBeInTheDocument()
  })

  it('sends a plain USER away from a reviewer-only route', () => {
    mockAuth.value = { isAuthenticated: true, loading: false, user: { role: 'USER' } }
    renderAt('/secret', ['REVIEWER', 'ADMIN'])
    expect(screen.getByText('user home')).toBeInTheDocument()
    expect(screen.queryByText('secret content')).not.toBeInTheDocument()
  })

  it('sends a REVIEWER away from an admin-only route to the reviewer console', () => {
    mockAuth.value = { isAuthenticated: true, loading: false, user: { role: 'REVIEWER' } }
    renderAt('/secret', ['ADMIN'])
    expect(screen.getByText('reviewer home')).toBeInTheDocument()
  })
})
