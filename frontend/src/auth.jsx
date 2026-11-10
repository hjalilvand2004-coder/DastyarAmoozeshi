import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from './api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('d360_user') || 'null') } catch { return null }
  })
  const [loading, setLoading] = useState(!!localStorage.getItem('d360_token'))

  const refresh = useCallback(async () => {
    if (!localStorage.getItem('d360_token')) { setLoading(false); return }
    try {
      const { data } = await api.get('/auth/me')
      setUser(data.user)
      localStorage.setItem('d360_user', JSON.stringify(data.user))
    } catch {
      localStorage.removeItem('d360_token')
      localStorage.removeItem('d360_user')
      setUser(null)
    }
    setLoading(false)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const signIn = useCallback((token, u) => {
    localStorage.setItem('d360_token', token)
    localStorage.setItem('d360_user', JSON.stringify(u))
    setUser(u)
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem('d360_token')
    localStorage.removeItem('d360_user')
    setUser(null)
  }, [])

  const can = (perm) => {
    if (!user) return false
    return user.permissions?.includes('*') || user.permissions?.includes(perm)
  }

  return (
    <AuthCtx.Provider value={{ user, loading, signIn, signOut, refresh, can }}>
      {children}
    </AuthCtx.Provider>
  )
}

export const useAuth = () => useContext(AuthCtx)
