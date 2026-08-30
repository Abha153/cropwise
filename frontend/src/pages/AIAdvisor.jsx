import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

export default function AIAdvisor() {
  const { user } = useAuth()
  const [crops, setCrops] = useState([])
  const [crop, setCrop] = useState('Tomato')
  const [quantity, setQuantity] = useState(1000)
  const [quality, setQuality] = useState('B')
  const [location, setLocation] = useState('Bilaspur')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { api.getCrops().then(setCrops) }, [])
  useEffect(() => { if (user?.location) setLocation(user.location) }, [user])
  useEffect(() => { if (user?.crops?.[0]) setCrop(user.crops[0]) }, [user])

  async function ask(e) {
    e?.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await api.advisorRecommend({ crop, quantity_kg: quantity, quality_grade: quality, location })
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const confTone = result?.recommendation.confidence_label === 'High' ? 'success' : result?.recommendation.confidence_label === 'Medium' ? 'marigold' : 'warning'

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">🤖 AgriAdvisor</h1>
      <p className="text-xs text-ink/40 dark:text-paper/40 mb-1">📦 Rule-based recommendation engine over demo market/weather data -- not a trained ML model, and not live weather.</p>
      <p className="text-ink/60 dark:text-paper/60 mb-6">An explainable recommendation on what, where, and when to sell -- never a black box.</p>

      <form onSubmit={ask} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
          <select value={crop} onChange={e => setCrop(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg)</label>
          <input type="number" min="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quality grade</label>
          <select value={quality} onChange={e => setQuality(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            <option value="A">A -- Premium</option>
            <option value="B">B -- Standard</option>
            <option value="C">C -- Basic</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Location</label>
          <input value={location} onChange={e => setLocation(e.target.value)} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <button disabled={loading} className="bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg py-2.5 transition-colors disabled:opacity-60">
          {loading ? 'Thinking...' : 'Get recommendation'}
        </button>
      </form>

      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2 mb-4">{error}</div>}
      {loading && <LoadingSpinner label="Analyzing prices, demand, and weather..." />}

      {result && !loading && (
        <div className="space-y-6">
          <div className="bg-forest text-paper rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <Badge tone={confTone}>{result.recommendation.confidence_label} confidence · {result.recommendation.confidence_pct}%</Badge>
            </div>
            <p className="font-display text-xl md:text-2xl font-semibold leading-snug mb-3">
              {result.recommendation.recommendation_text}
            </p>
            <p className="text-paper/80 text-sm">{result.recommendation.wait_rationale}</p>
            <div className="grid grid-cols-2 gap-4 mt-5 pt-5 border-t border-white/10">
              <div>
                <div className="text-xs text-paper/60 mb-0.5">Expected price range (7 days)</div>
                <div className="font-mono-data font-semibold">₹{result.recommendation.expected_price_range.low} -- ₹{result.recommendation.expected_price_range.high}/kg</div>
              </div>
              <div>
                <div className="text-xs text-paper/60 mb-0.5">Main risk</div>
                <div className="text-sm">{result.recommendation.primary_risk}</div>
              </div>
            </div>
          </div>

          <div>
            <h2 className="font-display font-semibold text-lg mb-3">Why this recommendation? (no black box)</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {result.recommendation.factors.map(f => (
                <div key={f.label} className="bg-white dark:bg-white/5 rounded-xl border border-black/5 dark:border-white/10 shadow-card p-4 text-center">
                  <div className="text-2xl mb-1">{f.icon}</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50 mb-0.5">{f.label}</div>
                  <div className="font-semibold text-sm">{f.value}</div>
                  {f.label === 'Weather Risk' && <div className="text-[10px] text-amber-600 mt-1">🟡 Demo weather (simulated)</div>}
                  {f.label === 'Supply / Arrivals' && <div className="text-[10px] text-amber-600 mt-1">🟡 Demo market data</div>}
                </div>
              ))}
            </div>
            <p className="text-xs text-ink/40 dark:text-paper/40 mt-2">Every factor above is a real input the recommendation engine used to reach its answer -- none are decorative. Market and weather figures come from CropWise's demo dataset, not a live feed.</p>
          </div>

          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <h2 className="font-display font-semibold text-lg mb-3">Market options considered</h2>
            <div className="space-y-2">
              {result.recommendation.market_options_considered.map(m => (
                <div key={m.market} className={`flex items-center justify-between text-sm px-3 py-2 rounded-lg ${m.market === result.recommendation.recommended_market ? 'bg-marigold/10 font-semibold' : ''}`}>
                  <span>{m.market === result.recommendation.recommended_market ? '🟢 ' : ''}{m.market} ({m.distance_km} km)</span>
                  <span className="font-mono-data">₹{m.net_profit.toLocaleString()} net profit</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
