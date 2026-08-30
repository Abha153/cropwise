import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'

export default function GroupSelling() {
  const { user } = useAuth()
  const [crops, setCrops] = useState([])
  const [pools, setPools] = useState(null)
  const [crop, setCrop] = useState('Chana (Gram)')
  const [quantity, setQuantity] = useState(500)
  const [fpoName, setFpoName] = useState('')
  const [joining, setJoining] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => { api.getCrops().then(setCrops) }, [])

  async function loadPools() {
    setPools(null)
    try {
      const data = await api.getGroupPools()
      setPools(data)
    } catch (e) {
      setPools([])
    }
  }
  useEffect(() => { loadPools() }, [])

  async function join(e) {
    e.preventDefault()
    setJoining(true)
    setMessage('')
    try {
      const res = await api.joinGroupPool({ crop, quantity_kg: quantity, fpo_name: fpoName || undefined })
      setMessage(`Joined "${res.fpo_name}" -- pool now has ${res.member_count} members and ${res.total_quantity_kg.toLocaleString()} kg.`)
      loadPools()
    } catch (e) {
      setMessage(e.message)
    } finally {
      setJoining(false)
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">🤝 Group Selling</h1>
      <p className="text-ink/60 dark:text-paper/60 mb-6">Pool produce with other farmers through your FPO / cooperative for stronger bargaining power.</p>

      <form onSubmit={join} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
          <select value={crop} onChange={e => setCrop(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Your quantity (kg)</label>
          <input type="number" min="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">FPO / group name</label>
          <input value={fpoName} onChange={e => setFpoName(e.target.value)} placeholder={user?.fpo_group || 'e.g. Bilaspur Kisan Producer Co.'} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <button disabled={joining} className="bg-forest text-paper font-semibold rounded-lg py-2.5 hover:bg-forest-dark transition-colors disabled:opacity-60">
          {joining ? 'Joining...' : 'Join / create pool'}
        </button>
      </form>

      {message && <div className="bg-marigold/10 border border-marigold/30 text-marigold-dark text-sm rounded-lg px-4 py-2.5 mb-6">{message}</div>}

      {pools === null ? <LoadingSpinner label="Loading pools..." /> : pools.length === 0 ? (
        <p className="text-sm text-ink/50 dark:text-paper/50">No open pools yet -- be the first to start one.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pools.map(p => (
            <div key={p.id} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-display font-semibold text-lg">{p.crop}</h3>
                <span className="text-xs text-ink/50 dark:text-paper/50">{p.fpo_name}</span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                <div><div className="text-xs text-ink/40 dark:text-paper/40">Members</div><div className="font-semibold">{p.member_count}</div></div>
                <div><div className="text-xs text-ink/40 dark:text-paper/40">Total quantity</div><div className="font-mono-data font-semibold">{p.total_quantity_kg.toLocaleString()} kg</div></div>
              </div>
              <div className="bg-forest/5 rounded-lg px-3 py-2 text-sm">
                <span className="font-semibold text-forest">+{p.estimated_price_improvement_pct}%</span> estimated price improvement from bulk negotiation with {p.potential_bulk_buyers} potential buyers.
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
