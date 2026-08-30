import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import StatCard from '../components/StatCard'
import LoadingSpinner from '../components/LoadingSpinner'
import Badge from '../components/Badge'

function AdminLogin({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await api.adminLogin(username, password)
      localStorage.setItem('cropwise_admin_token', data.access_token)
      onSuccess(data.access_token)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-16">
      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6">
        <h1 className="font-display text-xl font-bold mb-1">🔐 Admin Access</h1>
        <p className="text-sm text-ink/60 dark:text-paper/60 mb-4">The impact dashboard is protected -- sign in with the admin console credentials.</p>
        {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}
        <form onSubmit={submit} className="space-y-3">
          <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Admin username" autoComplete="username" className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Admin password" autoComplete="current-password" className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
          <button disabled={loading} className="w-full bg-forest text-paper font-semibold rounded-lg py-2.5 disabled:opacity-60">
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        {/*
          No credentials are ever shown here, hard-coded, or shipped in the
          frontend bundle. This form only forwards whatever you type to
          POST /auth/admin/login -- the backend checks it against
          ADMIN_USERNAME / ADMIN_PASSWORD, which live in the server
          environment only. If you don't know the credentials for this
          deployment, check that deployment's environment variables (or
          backend/.env locally) -- never this page's source.
        */}
        <p className="text-xs text-ink/40 dark:text-paper/40 mt-4">Don't have admin access? Ask whoever deployed this instance to check its ADMIN_USERNAME / ADMIN_PASSWORD environment variables.</p>
      </div>
    </div>
  )
}

function fmtDateTime(iso) {
  if (!iso) return 'Never'
  return new Date(iso).toLocaleString()
}

const LOGIN_STATUS_LABEL = {
  never_logged_in: 'Never logged in',
  active_today: 'Active today',
  active_this_week: 'Active this week',
  inactive: 'Inactive',
}
const LOGIN_STATUS_TONE = {
  never_logged_in: 'neutral',
  active_today: 'success',
  active_this_week: 'info',
  inactive: 'warning',
}

export default function AdminDashboard() {
  const [token, setToken] = useState(() => localStorage.getItem('cropwise_admin_token'))
  const [impact, setImpact] = useState(null)
  const [activity, setActivity] = useState(null)
  const [recent, setRecent] = useState(null)
  const [users, setUsers] = useState(null)
  const [userSearch, setUserSearch] = useState('')
  const [error, setError] = useState('')

  const handleAuthFailure = useCallback(() => {
    localStorage.removeItem('cropwise_admin_token')
    setToken(null)
  }, [])

  useEffect(() => {
    if (!token) return
    Promise.all([
      api.getImpact(token),
      api.getUserActivity(token),
      api.getRecentActivity(token, 20),
      api.getAdminUsers(token),
    ])
      .then(([impactData, activityData, recentData, usersData]) => {
        setImpact(impactData)
        setActivity(activityData)
        setRecent(recentData)
        setUsers(usersData)
      })
      .catch((err) => {
        setError(err.message)
        handleAuthFailure()
      })
  }, [token, handleAuthFailure])

  // Re-query just the user list when the admin searches by name/email --
  // no need to re-fetch impact/activity/recent-activity for that.
  useEffect(() => {
    if (!token) return
    const t = setTimeout(() => {
      api.getAdminUsers(token, { q: userSearch || undefined }).then(setUsers).catch(() => {})
    }, 250)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userSearch])

  if (!token) return <AdminLogin onSuccess={(t) => { setToken(t); setError('') }} />
  if (!impact || !activity || !recent || !users) return <LoadingSpinner label="Loading admin dashboard..." />

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="font-display text-3xl font-bold">📈 Impact Dashboard</h1>
        <button
          onClick={() => { localStorage.removeItem('cropwise_admin_token'); setToken(null) }}
          className="text-sm text-ink/50 dark:text-paper/50 hover:underline"
        >
          Sign out
        </button>
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-6">Platform-wide impact, computed live from real listings and transactions. Protected -- admin authentication required.</p>
      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}

      <div className="bg-forest text-paper rounded-2xl p-6 mb-6">
        <div className="text-xs uppercase tracking-wide text-marigold-light font-semibold mb-1">Estimated additional income generated for farmers</div>
        <div className="font-mono-data text-4xl font-bold">₹{impact.estimated_additional_farmer_income.toLocaleString()}</div>
        <p className="text-paper/70 text-sm mt-2">Sum of net-profit gains found by comparing markets vs. each farmer's nearest option.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard label="Farmers Connected" value={impact.farmers_connected} icon="🌾" />
        <StatCard label="Buyers Connected" value={impact.buyers_connected} icon="🏢" />
        <StatCard label="Produce Listed" value={`${impact.total_produce_listed_kg.toLocaleString()} kg`} icon="⚖️" />
        <StatCard label="Active Listings" value={impact.active_listings} icon="📋" />
        <StatCard label="Successful Transactions" value={impact.successful_transactions} icon="🤝" />
        <StatCard label="Transactions In Progress" value={impact.total_transactions_initiated - impact.successful_transactions} icon="⏳" />
        <StatCard label="Total Transaction Value" value={`₹${impact.total_transaction_value.toLocaleString()}`} icon="💰" />
        <StatCard label="Avg Price Improvement" value={`${impact.average_price_improvement_pct}%`} icon="📈" />
        <StatCard label="Transport Savings (FarmPool)" value={`₹${impact.estimated_transport_savings.toLocaleString()}`} icon="🚚" />
      </div>

      {/* ---------------- USER ACTIVITY ---------------- */}
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="font-display text-2xl font-bold">👤 User Activity</h2>
        <span className="text-xs text-ink/40 dark:text-paper/40 font-mono-data">as of {fmtDateTime(activity.as_of)} UTC</span>
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-4 text-sm">
        Whether registered accounts have actually logged in -- not just how many accounts exist.
        "Unique users" counts distinct people (by account id + role), not raw login requests.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <StatCard label="Total Registered Farmers" value={activity.total_registered_farmers} icon="🌾" />
        <StatCard label="Total Registered Buyers" value={activity.total_registered_buyers} icon="🏢" />
        <StatCard label="Registrations Today" value={activity.registrations_today} icon="🆕" />
        <StatCard label="Registrations This Week" value={activity.registrations_this_week} icon="🗓️" />
        <StatCard label="Unique Users Logged In Today" value={activity.unique_users_logged_in_today} icon="✅" tone="marigold" />
        <StatCard label="Unique Users Logged In This Week" value={activity.unique_users_logged_in_this_week} icon="✅" />
        <StatCard label="Successful Logins Today" value={activity.successful_login_events_today} icon="🔓" />
        <StatCard label="Successful Logins This Month" value={activity.successful_login_events_this_month} icon="🔓" />
        <StatCard label="Failed Login Attempts Today" value={activity.failed_login_attempts_today} icon="⚠️" />
      </div>

      {/* ---------------- RECENT ACTIVITY ---------------- */}
      <h2 className="font-display text-2xl font-bold mb-1">🕒 Recent Activity</h2>
      <p className="text-ink/60 dark:text-paper/60 mb-4 text-sm">Most recent login attempts, newest first. Never shown to normal users.</p>
      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 overflow-x-auto mb-10">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-forest/60 border-b border-black/5 dark:border-white/10">
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Login Time</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {recent.events.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-ink/40 dark:text-paper/40">No login activity recorded yet.</td></tr>
            )}
            {recent.events.map((e, i) => (
              <tr key={i} className="border-b border-black/5 dark:border-white/5 last:border-0">
                <td className="px-4 py-3">
                  <div className="font-semibold">{e.name || 'Unknown'}</div>
                  {e.email && <div className="text-xs text-ink/50 dark:text-paper/50">{e.email}</div>}
                </td>
                <td className="px-4 py-3 capitalize">{e.role}</td>
                <td className="px-4 py-3 font-mono-data text-xs">{fmtDateTime(e.login_time)}</td>
                <td className="px-4 py-3">
                  <Badge tone={e.success ? 'success' : 'warning'}>{e.success ? 'Success' : 'Failed'}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ---------------- REGISTERED USERS & LOGIN STATUS ---------------- */}
      <div className="flex items-center justify-between mb-1 gap-4 flex-wrap">
        <h2 className="font-display text-2xl font-bold">📋 Registered Users</h2>
        <input
          value={userSearch}
          onChange={e => setUserSearch(e.target.value)}
          placeholder="Search by name or email..."
          className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper w-64"
        />
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-4 text-sm">Look up whether a specific registered user has ever logged in.</p>
      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-forest/60 border-b border-black/5 dark:border-white/10">
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Registered</th>
              <th className="px-4 py-3">Last Login</th>
              <th className="px-4 py-3">Login Status</th>
            </tr>
          </thead>
          <tbody>
            {users.users.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-ink/40 dark:text-paper/40">No matching users.</td></tr>
            )}
            {users.users.map((u) => (
              <tr key={`${u.role}-${u.id}`} className="border-b border-black/5 dark:border-white/5 last:border-0">
                <td className="px-4 py-3">
                  <div className="font-semibold">{u.name}</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50">{u.email}</div>
                </td>
                <td className="px-4 py-3 capitalize">{u.role}</td>
                <td className="px-4 py-3 font-mono-data text-xs">{fmtDateTime(u.registered_at)}</td>
                <td className="px-4 py-3 font-mono-data text-xs">{fmtDateTime(u.last_login)}</td>
                <td className="px-4 py-3">
                  <Badge tone={LOGIN_STATUS_TONE[u.login_status] || 'neutral'}>{LOGIN_STATUS_LABEL[u.login_status] || u.login_status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
