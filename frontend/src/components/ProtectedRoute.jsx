import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LoadingSpinner } from './Feedback'

// Frontend route guard. This is a UX/navigation layer only -- every
// endpoint it gates is independently authorized by the FastAPI
// backend (see app/api/deps.py::require_role and the per-case
// ownership check in app/api/kyc.py). A user bypassing this component
// would still get a real 401/403 from the API, never real data.
//
// allowedRoles, when given, restricts the route to those roles
// (matches the user's `role` from GET /api/auth/me: USER / REVIEWER /
// ADMIN). Omit it for "any authenticated user".
export default function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink">
        <LoadingSpinner label="Loading session..." />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    // Authenticated but not permitted for this route -- send USER
    // accounts back to their dashboard and everyone else to a safe
    // default rather than showing a broken/empty reviewer page.
    const fallback = user?.role === 'REVIEWER' || user?.role === 'ADMIN' ? '/reviewer' : '/dashboard'
    return <Navigate to={fallback} replace />
  }

  return children
}
