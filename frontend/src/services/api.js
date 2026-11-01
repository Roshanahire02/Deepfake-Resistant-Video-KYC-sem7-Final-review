import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('kyc_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('kyc_token')
      localStorage.removeItem('kyc_role')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export function apiErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  return err?.response?.data?.detail || err?.message || fallback
}

export default api

// Authenticated report download. A plain <a href="/api/..."> sends no
// Authorization header (the JWT lives in localStorage), so the API
// would answer 401. This fetches through the axios client instead and
// saves the JSON report locally.
export async function downloadReport(caseId) {
  const res = await api.get(`/kyc/${caseId}/report`)
  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `kyc-report-${caseId.slice(0, 8)}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
