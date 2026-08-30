import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'
import Badge from '../components/Badge'

export default function Profile() {
  const { user, role, setUser } = useAuth()
  const [name, setName] = useState(user?.name || '')
  const [location, setLocation] = useState(user?.location || '')
  const [phone, setPhone] = useState(user?.phone || '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      const updated = await api.updateFarmerProfile({ name, location, phone })
      setUser(updated)
      localStorage.setItem('cropwise_user', JSON.stringify(updated))
      setMessage('Profile updated.')
    } catch (e) {
      setMessage(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="font-display text-3xl font-bold mb-1">👤 Profile</h1>
      <p className="text-ink/60 dark:text-paper/60 mb-6">Manage your account details.</p>

      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-14 h-14 rounded-full bg-forest text-paper flex items-center justify-center text-2xl font-display font-bold">
            {(role === 'buyer' ? user?.company_name : user?.name)?.[0]}
          </div>
          <div>
            <div className="font-display font-semibold text-lg">{role === 'buyer' ? user?.company_name : user?.name}</div>
            <Badge tone={role === 'buyer' ? 'forest' : 'marigold'}>{role === 'buyer' ? user?.buyer_type : 'Farmer'}</Badge>
          </div>
        </div>
        <div className="text-sm text-ink/60 dark:text-paper/60 space-y-1">
          <div>📧 {user?.email}</div>
          <div>📍 {user?.location}</div>
          {role === 'farmer' && user?.crops?.length > 0 && <div>🌱 Growing: {user.crops.join(', ')}</div>}
          {role === 'farmer' && user?.fpo_group && <div>🤝 FPO: {user.fpo_group}</div>}
          {role === 'farmer' && <div>⭐ Rating: {user?.rating}/5</div>}
          {role === 'buyer' && <div>⭐ Reliability: {user?.reliability_score}/100</div>}
        </div>
      </div>

      {role === 'farmer' && (
        <form onSubmit={save} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6 space-y-4">
          <h2 className="font-display font-semibold text-lg">Edit details</h2>
          {message && <div className="text-sm bg-marigold/10 text-marigold-dark rounded-lg px-3 py-2">{message}</div>}
          <div>
            <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Name</label>
            <input value={name} onChange={e => setName(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Location</label>
            <input value={location} onChange={e => setLocation(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Phone</label>
            <input value={phone} onChange={e => setPhone(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
          </div>
          <button disabled={saving} className="bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg px-5 py-2.5 transition-colors disabled:opacity-60">
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </form>
      )}
    </div>
  )
}
