import PageHeader from '../components/PageHeader'
import { SimpleCard } from '../components/Card'
import { useAuth } from '../context/AuthContext'
import Button from '../components/Button'
import { useNavigate } from 'react-router-dom'

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div>
      <PageHeader title="Profile" description="Your account details." />
      <SimpleCard title="Account" className="max-w-lg">
        <dl className="space-y-3 text-sm">
          <Row label="Full name" value={user?.full_name} />
          <Row label="Email" value={user?.email} />
          <Row label="Role" value={user?.role} />
          <Row label="User ID" value={<span className="mono text-xs">{user?.id}</span>} />
        </dl>
        <Button variant="outline" className="mt-6" onClick={handleLogout}>
          Sign out
        </Button>
      </SimpleCard>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-border-soft pb-3 last:border-0 last:pb-0">
      <dt className="text-text-muted">{label}</dt>
      <dd className="font-medium text-text">{value || '—'}</dd>
    </div>
  )
}
