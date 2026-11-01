import { useEffect, useState } from 'react'
import api, { apiErrorMessage } from '../services/api'
import PageHeader from '../components/PageHeader'
import { Card, CardContent } from '../components/Card'
import { LoadingSpinner, ErrorState, ErrorBanner } from '../components/Feedback'
import DataTable from '../components/DataTable'
import { Select } from '../components/Form'
import { useAuth } from '../context/AuthContext'

const ROLES = ['USER', 'REVIEWER', 'ADMIN']

// ADMIN-only. Uses GET /api/admin/users and PUT /api/admin/users/{id}/role
// (both enforced server-side; this route guard is only UX).
export default function AdminUsers() {
  const { user: me } = useAuth()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)

  useEffect(() => {
    api.get('/admin/users')
      .then((res) => setUsers(res.data))
      .catch((err) => setError(apiErrorMessage(err, 'Could not load users.')))
      .finally(() => setLoading(false))
  }, [])

  async function changeRole(u, role) {
    if (role === u.role) return
    setActionError('')
    setBusyId(u.id)
    try {
      await api.put(`/admin/users/${u.id}/role`, { role })
      setUsers((list) => list.map((x) => (x.id === u.id ? { ...x, role } : x)))
    } catch (err) {
      setActionError(apiErrorMessage(err, 'Could not change this role.'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="User Administration"
        breadcrumb={<span className="mono text-[11px] uppercase tracking-wider text-brand">Admin</span>}
        description="Review accounts and assign roles. Changes apply the next time the user signs in."
      />
      {loading && <LoadingSpinner label="Loading users..." />}
      {!loading && error && <ErrorState message={error} />}
      {!loading && !error && (
        <Card>
          <CardContent>
            <ErrorBanner message={actionError} />
            <DataTable
              rows={users}
              emptyMessage="No users."
              columns={[
                { key: 'full_name', header: 'Name' },
                { key: 'email', header: 'Email' },
                { key: 'case_count', header: 'Cases', render: (u) => <span className="mono">{u.case_count}</span> },
                {
                  key: 'role',
                  header: 'Role',
                  render: (u) => (
                    <div className="w-36">
                      <Select
                        aria-label={`Role for ${u.email}`}
                        value={u.role}
                        disabled={u.id === me?.id || busyId === u.id}
                        onChange={(e) => changeRole(u, e.target.value)}
                      >
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </Select>
                    </div>
                  ),
                },
              ]}
            />
            <p className="mt-3 text-[11px] text-text-faint">You cannot change your own role.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
