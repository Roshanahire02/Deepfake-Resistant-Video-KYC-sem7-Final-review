import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { LoadingSpinner } from './components/Feedback'
import PublicLayout from './layouts/PublicLayout'
import AppShell from './layouts/AppShell'
import ProtectedRoute from './components/ProtectedRoute'

const Landing = lazy(() => import('./pages/Landing'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const CreateCase = lazy(() => import('./pages/CreateCase'))
const CaseList = lazy(() => import('./pages/CaseList'))
const CaseDetail = lazy(() => import('./pages/CaseDetail'))
const Results = lazy(() => import('./pages/Results'))
const Profile = lazy(() => import('./pages/Profile'))
const ModelStatus = lazy(() => import('./pages/ModelStatus'))

const ReviewerDashboard = lazy(() => import('./pages/reviewer/ReviewerDashboard'))
const ReviewerCases = lazy(() => import('./pages/reviewer/ReviewerCases'))
const ReviewerQueue = lazy(() => import('./pages/reviewer/ReviewerQueue'))
const ReviewerReports = lazy(() => import('./pages/reviewer/ReviewerReports'))
const ReviewerCaseDetail = lazy(() => import('./pages/reviewer/ReviewerCaseDetail'))
const AdminUsers = lazy(() => import('./pages/AdminUsers'))

export default function App() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center"><LoadingSpinner label="Loading..." /></div>}>
    <Routes>
      {/* Public */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Authenticated -- any role */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/models" element={<ModelStatus />} />
        <Route path="/profile" element={<Profile />} />

        {/* USER-only */}
        <Route path="/dashboard" element={<ProtectedRoute allowedRoles={['USER']}><Dashboard /></ProtectedRoute>} />
        <Route path="/new-kyc" element={<ProtectedRoute allowedRoles={['USER']}><CreateCase /></ProtectedRoute>} />
        <Route path="/kyc/new" element={<Navigate to="/new-kyc" replace />} />
        <Route path="/cases" element={<ProtectedRoute allowedRoles={['USER']}><CaseList /></ProtectedRoute>} />
        <Route path="/cases/:caseId" element={<ProtectedRoute allowedRoles={['USER']}><CaseDetail /></ProtectedRoute>} />
        <Route path="/results" element={<ProtectedRoute allowedRoles={['USER']}><Results /></ProtectedRoute>} />

        {/* ADMIN-only */}
        <Route path="/admin" element={<ProtectedRoute allowedRoles={['ADMIN']}><AdminUsers /></ProtectedRoute>} />

        {/* REVIEWER/ADMIN-only */}
        <Route path="/reviewer" element={<ProtectedRoute allowedRoles={['REVIEWER', 'ADMIN']}><ReviewerDashboard /></ProtectedRoute>} />
        <Route path="/reviewer/cases" element={<ProtectedRoute allowedRoles={['REVIEWER', 'ADMIN']}><ReviewerCases /></ProtectedRoute>} />
        <Route path="/reviewer/queue" element={<ProtectedRoute allowedRoles={['REVIEWER', 'ADMIN']}><ReviewerQueue /></ProtectedRoute>} />
        <Route path="/reviewer/reports" element={<ProtectedRoute allowedRoles={['REVIEWER', 'ADMIN']}><ReviewerReports /></ProtectedRoute>} />
        <Route path="/reviewer/cases/:caseId" element={<ProtectedRoute allowedRoles={['REVIEWER', 'ADMIN']}><ReviewerCaseDetail /></ProtectedRoute>} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}
