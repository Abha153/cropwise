import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import Badge from '../components/Badge'

/**
 * Phase 18 — Market Intelligence → Best Selling Action
 * Combines: Mandi Price + Forecast + Buyer Demand + Quality + Transport/Storage Cost
 * into a single BEST OPTION recommendation.
 */

export default function BestOption() {
  const { user, role } = useAuth()
  const [crops, setCrops] = useState([])
  const [markets, setMarkets] = useState([])
  const [crop, setCrop] = useState('Soybean')
  const [location, setLocation] = useState('Bilaspur')
  const [quantity, setQuantity] = useState(1000)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [marketData, setMarketData] = useState(null)
  const [buyerMatches, setBuyerMatches] = useState([])
  const [sellingWindow, setSellingWindow] = useState(null)
  const [demands, setDemands] = useState([])

  useEffect(() => {
    api.getCrops().then(d => { setCrops(d); if (d.length) setCrop(d[0].name) }).catch(() => {})
    api.getMarkets().then(setMarkets).catch(() => {})
  }, [])

  useEffect(() => {
    if (role === 'farmer' && user?.location) setLocation(user.location)
  }, [user, role])

  async function loadAll() {
    setLoading(true)
    setError('')
    try {
      const [market, window_, demandsData] = await Promise.all([
        api.compareMarkets(crop, quantity, location).catch(() => null),
        api.getSellingWindow(crop, location, quantity).catch(() => null),
        api.getDemands({ crop, status: 'ACTIVE' }).catch(() => []),
      ])
      setMarketData(market)
      setSellingWindow(window_)
      setDemands(Array.isArray(demandsData) ? demandsData.slice(0, 3) : [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (crop && location) loadAll() }, [crop, location])

  // Find best mandi option
  const bestMandi = marketData?.options?.[0]
  // Find best buyer demand match
  const bestDemand = demands[0]

  // Determine best overall option
  let bestOptionType = null
  let bestOptionLabel = ''
  if (bestDemand && bestMandi) {
    const demandNetRev = bestDemand.target_price_per_kg * quantity
    const mandiNetRev = bestMandi.net_profit
    bestOptionType = demandNetRev > mandiNetRev ? 'buyer' : 'mandi'
  } else if (bestDemand) {
    bestOptionType = 'buyer'
  } else if (bestMandi) {
    bestOptionType = 'mandi'
  }

  bestOptionLabel = bestOptionType === 'buyer'
    ? `Sell to Buyer: ${bestDemand?.buyer_name || 'Verified Buyer'}`
    : bestMandi ? `Sell at ${bestMandi.market} Mandi` : 'Insufficient data'

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">🎯 Best Selling Option</h1>
      <p className="text-ink/60 dark:text-paper/60 mb-6">
        All market intelligence combined into one actionable recommendation.
      </p>

      {/* Controls */}
      <div className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
          <select value={crop} onChange={e => setCrop(e.target.value)}
            className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Your Location</label>
          <select value={location} onChange={e => setLocation(e.target.value)}
            className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {markets.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg)</label>
          <input type="number" value={quantity} min="1"
            onChange={e => setQuantity(Number(e.target.value))}
            className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm w-28 bg-white dark:bg-white/5 dark:text-paper" />
        </div>
        <button onClick={loadAll}
          className="bg-forest text-paper px-4 py-2 rounded-lg text-sm font-semibold hover:bg-forest/90">
          Analyse
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <div className="text-red-500 text-sm mb-4">{error}</div>}

      {!loading && (bestMandi || bestDemand) && (
        <>
          {/* BEST OPTION BANNER */}
          <div className="bg-forest text-paper rounded-2xl p-6 mb-6">
            <p className="text-xs font-medium opacity-70 uppercase tracking-widest mb-1">Best Option</p>
            <h2 className="font-display text-2xl font-bold mb-3">{bestOptionLabel}</h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {bestOptionType === 'buyer' && bestDemand && (
                <>
                  <div><p className="text-xs opacity-70">Buyer Price</p><p className="font-bold text-lg">₹{bestDemand.target_price_per_kg}/kg</p></div>
                  <div><p className="text-xs opacity-70">Mandi Price</p><p className="font-bold">{bestMandi ? `₹${bestMandi.modal_price_per_kg}/kg` : '—'}</p></div>
                  <div><p className="text-xs opacity-70">Transport Est.</p><p className="font-bold">{bestMandi ? `₹${bestMandi.transport_cost?.toFixed(0) || 0}` : '—'}</p></div>
                  <div><p className="text-xs opacity-70">Verification</p><p className="font-bold">{bestDemand.buyer_verified ? '✓ Verified' : 'Not verified'}</p></div>
                </>
              )}
              {bestOptionType === 'mandi' && bestMandi && (
                <>
                  <div><p className="text-xs opacity-70">Modal Price</p><p className="font-bold text-lg">₹{bestMandi.modal_price_per_kg}/kg</p></div>
                  <div><p className="text-xs opacity-70">Transport</p><p className="font-bold">₹{bestMandi.transport_cost?.toFixed(0) || 0}</p></div>
                  <div><p className="text-xs opacity-70">Net Revenue</p><p className="font-bold">₹{bestMandi.net_profit?.toLocaleString('en-IN')}</p></div>
                  <div><p className="text-xs opacity-70">Distance</p><p className="font-bold">{bestMandi.distance_km} km</p></div>
                </>
              )}
            </div>
          </div>

          {/* Side-by-side comparison */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">

            {/* Mandi Options */}
            <div className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">🏛️ Mandi Options</h3>
              {marketData?.options?.length > 0 ? (
                <div className="space-y-2">
                  {marketData.options.slice(0, 4).map((opt, i) => (
                    <div key={i} className={`p-2 rounded-lg text-sm ${i === 0 ? 'bg-forest/10 border border-forest/20' : 'bg-black/3 dark:bg-white/5'}`}>
                      <div className="flex justify-between">
                        <span className="font-semibold">{opt.market}</span>
                        <span className="font-bold">₹{opt.modal_price_per_kg}/kg</span>
                      </div>
                      <div className="flex justify-between text-xs text-ink/50 dark:text-paper/50">
                        <span>{opt.distance_km} km away</span>
                        <span>Net ₹{opt.net_profit?.toLocaleString('en-IN')}</span>
                      </div>
                      {opt.data_source === 'demo' && <span className="text-xs text-amber-500">⚠️ Demo</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-ink/40 dark:text-paper/40">No mandi data available</p>
              )}
            </div>

            {/* Buyer Demands */}
            <div className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">🤝 Active Buyer Demands</h3>
              {demands.length > 0 ? (
                <div className="space-y-2">
                  {demands.map((d, i) => (
                    <div key={i} className={`p-2 rounded-lg text-sm ${i === 0 ? 'bg-forest/10 border border-forest/20' : 'bg-black/3 dark:bg-white/5'}`}>
                      <div className="flex justify-between">
                        <span className="font-semibold">{d.buyer_name || 'Buyer'}</span>
                        <span className="font-bold">₹{d.target_price_per_kg}/kg</span>
                      </div>
                      <div className="text-xs text-ink/50 dark:text-paper/50">
                        {d.required_quantity_kg} kg • {d.delivery_location}
                      </div>
                      {d.buyer_verified && <span className="text-xs text-emerald-600">✓ Verified</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-ink/40 dark:text-paper/40">No active buyer demands for {crop}</p>
              )}
            </div>

            {/* Selling Window */}
            <div className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-4">
              <h3 className="font-bold mb-3 flex items-center gap-2">📅 Selling Window</h3>
              {sellingWindow ? (
                <>
                  <div className="mb-2">
                    <p className="text-xs text-ink/50 dark:text-paper/50">Current Price</p>
                    <p className="font-bold">₹{sellingWindow.current_price}/kg</p>
                  </div>
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-forest uppercase tracking-wide">Recommendation</p>
                    <p className="font-bold">{sellingWindow.recommendation?.replace(/_/g, ' ')}</p>
                  </div>
                  {sellingWindow.is_demo && (
                    <p className="text-xs text-amber-500 mb-2">⚠️ Demo forecast</p>
                  )}
                  <div className="space-y-1">
                    {sellingWindow.options?.slice(0, 3).map(opt => (
                      <div key={opt.label} className={`flex justify-between text-xs p-1.5 rounded ${opt.label === sellingWindow.recommendation ? 'bg-forest/10 font-semibold' : ''}`}>
                        <span>{opt.label?.replace(/_/g, ' ')}</span>
                        <span>₹{opt.estimated_net_revenue?.toLocaleString('en-IN')}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-ink/40 dark:text-paper/40">No forecast data available</p>
              )}
            </div>
          </div>

          {/* Action buttons for farmer */}
          {role === 'farmer' && (
            <div className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-5">
              <h3 className="font-bold mb-3">Take Action</h3>
              <div className="flex flex-wrap gap-3">
                <a href="/lots" className="bg-forest text-paper px-4 py-2 rounded-lg text-sm font-semibold hover:bg-forest/90">
                  📦 Create Crop Lot
                </a>
                <a href="/buyer-demands" className="border border-forest text-forest px-4 py-2 rounded-lg text-sm font-semibold hover:bg-forest/5">
                  🤝 Browse Buyer Demands
                </a>
                <a href="/market-intelligence" className="border border-black/10 dark:border-white/10 text-ink dark:text-paper px-4 py-2 rounded-lg text-sm font-semibold hover:bg-black/5">
                  📊 Full Market Analysis
                </a>
                <a href="/storage" className="border border-black/10 dark:border-white/10 text-ink dark:text-paper px-4 py-2 rounded-lg text-sm font-semibold hover:bg-black/5">
                  🏭 Find Storage
                </a>
              </div>
            </div>
          )}
        </>
      )}

      {!loading && !bestMandi && !bestDemand && !error && (
        <div className="text-center py-12 text-ink/40 dark:text-paper/40">
          <p className="text-4xl mb-3">🎯</p>
          <p className="font-medium">Select a crop and location to see the best selling options</p>
        </div>
      )}
    </div>
  )
}
