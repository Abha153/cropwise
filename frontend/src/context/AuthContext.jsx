import React, { createContext, useContext, useState, useCallback } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('cropwise_token'))
  const [role, setRole] = useState(() => localStorage.getItem('cropwise_role'))
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('cropwise_user')
    return raw ? JSON.parse(raw) : null
  })

  const applySession = useCallback((data) => {
    localStorage.setItem('cropwise_token', data.access_token)
    localStorage.setItem('cropwise_role', data.role)
    localStorage.setItem('cropwise_user', JSON.stringify(data.user))
    setToken(data.access_token)
    setRole(data.role)
    setUser(data.user)
  }, [])

  const loginFarmer = useCallback(async (email, password) => {
    const data = await api.loginFarmer(email, password)
    applySession(data)
    return data
  }, [applySession])

  const registerFarmer = useCallback(async (payload) => {
    const data = await api.registerFarmer(payload)
    applySession(data)
    return data
  }, [applySession])

  const registerBuyer = useCallback(async (payload) => {
    const data = await api.registerBuyer(payload)
    applySession(data)
    return data
  }, [applySession])

  const logout = useCallback(() => {
    localStorage.removeItem('cropwise_token')
    localStorage.removeItem('cropwise_role')
    localStorage.removeItem('cropwise_user')
    setToken(null)
    setRole(null)
    setUser(null)
  }, [])

  const value = {
    token, role, user, isAuthenticated: !!token,
    loginFarmer, registerFarmer, registerBuyer, logout, setUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
