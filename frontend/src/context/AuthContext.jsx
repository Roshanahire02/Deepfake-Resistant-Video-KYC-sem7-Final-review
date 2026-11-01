import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('kyc_token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadMe = useCallback(async () => {
    if (!localStorage.getItem('kyc_token')) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const res = await api.get('/auth/me')
      setUser(res.data)
    } catch {
      setUser(null)
      localStorage.removeItem('kyc_token')
      setToken(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMe()
  }, [loadMe])

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem('kyc_token', res.data.access_token)
    localStorage.setItem('kyc_role', res.data.role)
    setToken(res.data.access_token)
    await loadMe()
    return res.data
  }

  async function register(email, fullName, password) {
    await api.post('/auth/register', { email, full_name: fullName, password })
    return login(email, password)
  }

  function logout() {
    localStorage.removeItem('kyc_token')
    localStorage.removeItem('kyc_role')
    setToken(null)
    setUser(null)
  }

  const value = {
    token,
    user,
    loading,
    isAuthenticated: !!token && !!user,
    isReviewer: user?.role === 'REVIEWER' || user?.role === 'ADMIN',
    login,
    register,
    logout,
    refresh: loadMe,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
