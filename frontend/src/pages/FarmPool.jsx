import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'

export default function FarmPool() {
  const { user } = useAuth()
  const [crops, setCrops] = useState([])
  const [markets, setMarkets] = useState([])
  const [crop, setCrop] = useState('Tomato')
  const [location, setLocation] = useState('Bilaspur')
  const [quantity, setQuantity] = useState(500)
  const [destination, setDestination] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getCrops().then(setCrops)
    api.getMarkets().then(setMarkets)
  }, [])
  useEffect(() => { if (user?.location) setLocation(user.location) }, [user])

  async function run(e) {
    e?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await api.farmPool({ crop, location, quantity_kg: quantity, destination_market: destination || undefined })
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">🚚 FarmPool</h1>
      <p className="text-ink/60 dark:text-paper/60 mb-6">Combine your shipment with nearby farmers heading to the same market and split the truck cost.</p>

      <form onSubmit={run} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
          <select value={crop} onChange={e => setCrop(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Your location</label>
          <input value={location} onChange={e => setLocation(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg)</label>
          <input type="number" min="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Destination market</label>
          <select value={destination} onChange={e => setDestination(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            <option value="">Nearest market</option>
            {markets.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
        </div>
        <button disabled={loading} className="bg-forest text-paper font-semibold rounded-lg py-2.5 hover:bg-forest-dark transition-colors disabled:opacity-60">
          {loading ? 'Finding pool...' : 'Find shared transport'}
        </button>
      </form>

      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}
      {loading && <LoadingSpinner label="Looking for nearby farmers..." />}

      {result && !loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">Individual transport cost</div>
              <div className="font-mono-data text-2xl font-semibold">₹{result.your_individual_transport_cost.toLocaleString()}</div>
            </div>
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="text-xs text-ink/50 dark:text-paper/50 mb-1">Your shared cost</div>
              <div className="font-mono-data text-2xl font-semibold">₹{result.your_shared_transport_cost.toLocaleString()}</div>
            </div>
            <div className="bg-forest text-paper rounded-2xl p-5">
              <div className="text-xs text-marigold-light mb-1">You save</div>
              <div className="font-mono-data text-2xl font-semibold">₹{result.estimated_savings.toLocaleString()} ({result.savings_pct}%)</div>
            </div>
          </div>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <h2 className="font-display font-semibold text-lg mb-1">Pool to {result.destination_market} ({result.distance_km} km)</h2>
            <p className="text-sm text-ink/50 dark:text-paper/50 mb-4">Total pooled quantity: {result.total_pool_quantity_kg.toLocaleString()} kg</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between bg-marigold/10 rounded-lg px-3 py-2 text-sm font-semibold">
                <span>You</span><span className="font-mono-data">{result.your_quantity_kg.toLocaleString()} kg</span>
              </div>
              {result.pool_partners.map((p, i) => (
                <div key={i} className="flex items-center justify-between bg-wheat/50 rounded-lg px-3 py-2 text-sm">
                  <span>{p.farmer_name} · {p.distance_from_you_km} km away</span>
                  <span className="font-mono-data">{p.quantity_kg.toLocaleString()} kg</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
