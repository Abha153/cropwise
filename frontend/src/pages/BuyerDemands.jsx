import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const CROPS = [
  'Tomato', 'Onion', 'Potato', 'Wheat', 'Paddy (Rice)', 'Maize',
  'Soybean', 'Chana (Gram)', 'Groundnut', 'Mustard'
]

const STATUS_TONE = {
  ACTIVE: 'success', PARTIALLY_FILLED: 'info',
  FULFILLED: 'forest', EXPIRED: 'neutral', CANCELLED: 'neutral'
}

const PAYMENT_TERMS_OPTIONS = [
  'Advance 50%, balance on delivery',
  'Full payment on delivery',
  'Full payment within 7 days of delivery',
  'Cash on delivery',
  'NEFT within 3 days of delivery',
]

function DemandCard({ demand, buyerMap, role, onRespond, onCancel }) {
  const [showDetail, setShowDetail] = useState(false)
  const buyer = buyerMap[demand.buyer_id] || {}

  const isVerified = buyer.verification_status === 'verified'

  return (
    <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
      <div className="flex items-start justify-between mb-3 gap-2 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-display font-bold text-lg">{demand.crop}</span>
            <Badge tone={STATUS_TONE[demand.status] || 'neutral'}>{demand.status}</Badge>
            {isVerified && (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                ✓ Verified Buyer
              </span>
            )}
          </div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">
            {buyer.company_name || `Buyer #${demand.buyer_id}`}
            {demand.delivery_location && ` · Delivery: ${demand.delivery_location}`}
          </div>
        </div>
        <div className="text-right">
          {demand.target_price_per_kg && (
            <div className="font-mono-data font-bold text-forest text-lg">
              ₹{(demand.target_price_per_kg * 100).toFixed(0)}/q
            </div>
          )}
          <div className="text-xs text-ink/40 dark:text-paper/40">Target price</div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-3">
        <div>
          <div className="text-xs text-ink/40 dark:text-paper/40">Required</div>
          <div className="font-semibold">
            {demand.minimum_quantity_kg?.toLocaleString() || (demand.required_quantity_kg * 0.7).toFixed(0)}
            –{(demand.maximum_quantity_kg || demand.required_quantity_kg * 1.3).toLocaleString()} kg
          </div>
        </div>
        {demand.quality_grade && (
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Min Grade</div>
            <div className="font-semibold">Grade {demand.quality_grade}</div>
          </div>
        )}
        {demand.moisture_limit && (
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Moisture</div>
            <div className="font-semibold">≤{demand.moisture_limit}%</div>
          </div>
        )}
        {demand.delivery_deadline && (
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Deadline</div>
            <div className="font-semibold">{demand.delivery_deadline}</div>
          </div>
        )}
      </div>

      {demand.payment_terms && (
        <div className="text-xs text-ink/50 dark:text-paper/50 mb-3">
          💳 {demand.payment_terms}
        </div>
      )}

      {demand.additional_requirements && (
        <div className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 rounded-lg px-2 py-1 mb-3">
          📋 {demand.additional_requirements}
        </div>
      )}

      <div className="flex items-center gap-3 flex-wrap">
        {role === 'farmer' && demand.status === 'ACTIVE' && (
          <button
            onClick={() => onRespond(demand)}
            className="text-sm bg-forest text-paper font-semibold rounded-lg px-4 py-2"
          >
            Respond with a Lot →
          </button>
        )}
        {role === 'buyer' && (
          <>
            <button
              onClick={() => setShowDetail(s => !s)}
              className="text-sm text-forest font-semibold hover:underline"
            >
              {showDetail ? 'Hide details' : 'View matches →'}
            </button>
            {demand.status === 'ACTIVE' && (
              <button
                onClick={() => onCancel(demand.id)}
                className="text-sm text-red-500 hover:underline"
              >
                Cancel
              </button>
            )}
          </>
        )}
      </div>

      {showDetail && role === 'buyer' && (
        <DemandMatchPanel demandId={demand.id} />
      )}
    </div>
  )
}

function DemandMatchPanel({ demandId }) {
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.demandMatches(demandId)
      .then(setResult)
      .catch(e => setError(e.message))
  }, [demandId])

  if (error) return <div className="mt-3 text-xs text-red-600">{error}</div>
  if (!result) return <div className="mt-3 text-xs text-ink/50">Loading matches…</div>

  return (
    <div className="mt-4 border-t border-black/5 dark:border-white/10 pt-4">
      <h4 className="text-sm font-semibold mb-2">Matching lots & listings ({result.matches?.length || 0})</h4>
      {result.matches?.length === 0 ? (
        <p className="text-xs text-ink/50 dark:text-paper/50">No matching lots found yet.</p>
      ) : (
        <div className="space-y-2">
          {result.matches.map(m => (
            <div key={`${m.source}-${m.id}`} className="bg-wheat/40 dark:bg-white/5 rounded-lg px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold">{m.farmer_name}</span>
                  <span className="text-xs text-ink/50 dark:text-paper/50 ml-1">· {m.farmer_location}</span>
                  {m.lot_number && <span className="ml-1 text-xs text-ink/40">({m.lot_number})</span>}
                </div>
                <span className="font-mono-data font-bold text-forest">{m.match_score}%</span>
              </div>
              <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">
                {m.quantity_kg?.toLocaleString()} kg · Grade {m.grade} · ₹{(m.expected_price_per_kg * 100).toFixed(0)}/q
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CreateDemandForm({ onCreated, onClose }) {
  const [form, setForm] = useState({
    crop: 'Tomato',
    required_quantity_kg: 2000,
    minimum_quantity_kg: '',
    maximum_quantity_kg: '',
    target_price_per_kg: '',
    quality_grade: 'A',
    moisture_limit: '',
    foreign_matter_limit: '',
    damaged_grains_limit: '',
    delivery_location: '',
    delivery_deadline: '',
    payment_terms: PAYMENT_TERMS_OPTIONS[0],
    additional_requirements: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function set(field) { return e => setForm(f => ({ ...f, [field]: e.target.value })) }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (form.required_quantity_kg <= 0) { setError('Required quantity must be > 0'); return }
    setSubmitting(true)
    try {
      const payload = {
        crop: form.crop,
        required_quantity_kg: Number(form.required_quantity_kg),
        minimum_quantity_kg: form.minimum_quantity_kg ? Number(form.minimum_quantity_kg) : null,
        maximum_quantity_kg: form.maximum_quantity_kg ? Number(form.maximum_quantity_kg) : null,
        target_price_per_kg: form.target_price_per_kg ? Number(form.target_price_per_kg) / 100 : null,
        quality_grade: form.quality_grade || null,
        moisture_limit: form.moisture_limit ? Number(form.moisture_limit) : null,
        foreign_matter_limit: form.foreign_matter_limit ? Number(form.foreign_matter_limit) : null,
        damaged_grains_limit: form.damaged_grains_limit ? Number(form.damaged_grains_limit) : null,
        delivery_location: form.delivery_location || null,
        delivery_deadline: form.delivery_deadline || null,
        payment_terms: form.payment_terms || null,
        additional_requirements: form.additional_requirements || null,
      }
      await api.createDemand(payload)
      onCreated()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const inp = 'w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper'
  const lbl = 'text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1'

  return (
    <form onSubmit={submit} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 space-y-4">
      <h2 className="font-display font-semibold text-lg">Post a new buying demand</h2>
      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2">{error}</div>}

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className={lbl}>Crop</label>
          <select value={form.crop} onChange={set('crop')} className={inp}>
            {CROPS.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className={lbl}>Required quantity (kg)</label>
          <input type="number" min="1" value={form.required_quantity_kg} onChange={set('required_quantity_kg')} className={inp} required />
        </div>
        <div>
          <label className={lbl}>Min quantity (kg)</label>
          <input type="number" min="0" value={form.minimum_quantity_kg} onChange={set('minimum_quantity_kg')} className={inp} placeholder="Optional" />
        </div>
        <div>
          <label className={lbl}>Max quantity (kg)</label>
          <input type="number" min="0" value={form.maximum_quantity_kg} onChange={set('maximum_quantity_kg')} className={inp} placeholder="Optional" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className={lbl}>Target price (₹/quintal)</label>
          <input type="number" min="0" value={form.target_price_per_kg} onChange={set('target_price_per_kg')} className={inp} placeholder="e.g. 2800" />
        </div>
        <div>
          <label className={lbl}>Min grade required</label>
          <select value={form.quality_grade} onChange={set('quality_grade')} className={inp}>
            <option value="">Any</option>
            <option>A</option><option>B</option><option>C</option>
          </select>
        </div>
        <div>
          <label className={lbl}>Max moisture (%)</label>
          <input type="number" min="0" max="100" step="0.1" value={form.moisture_limit} onChange={set('moisture_limit')} className={inp} placeholder="e.g. 12" />
        </div>
        <div>
          <label className={lbl}>Max foreign matter (%)</label>
          <input type="number" min="0" max="100" step="0.1" value={form.foreign_matter_limit} onChange={set('foreign_matter_limit')} className={inp} placeholder="e.g. 2" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <label className={lbl}>Delivery location</label>
          <input value={form.delivery_location} onChange={set('delivery_location')} className={inp} placeholder="e.g. Raipur" />
        </div>
        <div>
          <label className={lbl}>Delivery deadline</label>
          <input type="date" value={form.delivery_deadline} onChange={set('delivery_deadline')} className={inp} />
        </div>
        <div>
          <label className={lbl}>Payment terms</label>
          <select value={form.payment_terms} onChange={set('payment_terms')} className={inp}>
            {PAYMENT_TERMS_OPTIONS.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className={lbl}>Additional requirements (optional)</label>
        <textarea value={form.additional_requirements} onChange={set('additional_requirements')} rows={2} className={`${inp} resize-none`} placeholder="Packaging, certification, specific variety..." />
      </div>

      <div className="flex items-center gap-3">
        <button disabled={submitting} className="bg-marigold hover:bg-amber-400 text-ink font-semibold rounded-lg px-5 py-2.5 disabled:opacity-60">
          {submitting ? 'Posting…' : 'Post demand'}
        </button>
        <button type="button" onClick={onClose} className="text-sm text-ink/50 hover:underline">Cancel</button>
      </div>
    </form>
  )
}

function RespondWithLotModal({ demand, onDone, onClose }) {
  const [lots, setLots] = useState(null)
  const [selectedLot, setSelectedLot] = useState(null)
  const [offerPrice, setOfferPrice] = useState('')
  const [offerQty, setOfferQty] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.myLots().then(setLots).catch(() => setLots([]))
  }, [])

  const matchingLots = (lots || []).filter(l =>
    l.crop === demand.crop && l.status === 'AVAILABLE'
  )

  function selectLot(l) {
    setSelectedLot(l)
    // Sensible defaults: buyer's target price (₹/kg from ₹/quintal-ish demand
    // field is already per kg here), quantity capped at both the lot and demand.
    setOfferPrice(String(demand.target_price_per_kg || l.expected_price || ''))
    setOfferQty(String(Math.min(l.quantity_kg, demand.required_quantity_kg || l.quantity_kg)))
  }

  async function submitOffer() {
    if (!selectedLot) return
    setSubmitting(true); setError('')
    try {
      const offer = await api.createOffer({
        lot_id: selectedLot.id,
        buyer_demand_id: demand.id,
        offered_price_per_kg: parseFloat(offerPrice),
        quantity_kg: parseFloat(offerQty),
        message: `Responding to demand #${demand.id} for ${demand.crop}`,
      })
      onDone(selectedLot, offer)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-stone-900 rounded-2xl p-6 max-w-lg w-full shadow-xl">
        <h3 className="font-display font-bold text-lg mb-1">Respond to demand</h3>
        <p className="text-sm text-ink/60 dark:text-paper/60 mb-4">
          Select one of your available {demand.crop} lots to send a real offer to this buyer.
        </p>
        {error && <div className="mb-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 text-red-600 text-xs rounded-lg">{error}</div>}
        {lots === null ? <LoadingSpinner label="Loading your lots…" /> : matchingLots.length === 0 ? (
          <div className="text-sm text-ink/50 dark:text-paper/50 py-4">
            No available {demand.crop} lots. <a href="/lots" className="text-forest underline">Create a lot first →</a>
          </div>
        ) : (
          <div className="space-y-2 mb-4">
            {matchingLots.map(l => (
              <label key={l.id} className={`flex items-center gap-3 border rounded-lg px-3 py-2.5 cursor-pointer ${selectedLot?.id === l.id ? 'border-forest bg-forest/5' : 'border-black/10 dark:border-white/15'}`}>
                <input type="radio" name="lot" onChange={() => selectLot(l)} checked={selectedLot?.id === l.id} />
                <div className="flex-1 text-sm">
                  <div className="font-semibold">{l.lot_number} — {l.quantity_kg.toLocaleString()} kg</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50">Grade {l.grade} · AI Score {l.quality_score}% · ₹{(l.expected_price * 100).toFixed(0)}/q</div>
                </div>
              </label>
            ))}
          </div>
        )}
        {selectedLot && (
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Offer price (₹/kg)</label>
              <input type="number" step="0.01" value={offerPrice} onChange={e => setOfferPrice(e.target.value)}
                className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg)</label>
              <input type="number" value={offerQty} onChange={e => setOfferQty(e.target.value)}
                className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
            </div>
          </div>
        )}
        <div className="flex gap-3">
          {selectedLot && (
            <button onClick={submitOffer} disabled={submitting}
              className="bg-forest text-paper text-sm font-semibold rounded-lg px-4 py-2 disabled:opacity-60">
              {submitting ? 'Sending offer…' : 'Send offer to buyer →'}
            </button>
          )}
          <button onClick={onClose} className="text-sm text-ink/50 hover:underline">Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default function BuyerDemands() {
  const { role } = useAuth()
  const [demands, setDemands] = useState(null)
  const [buyerMap, setBuyerMap] = useState({})
  const [showForm, setShowForm] = useState(false)
  const [cropFilter, setCropFilter] = useState('')
  const [respondTo, setRespondTo] = useState(null)
  const [toast, setToast] = useState('')
  const [error, setError] = useState('')

  const loadDemands = useCallback(async () => {
    setError('')
    try {
      const data = role === 'buyer'
        ? await api.myDemands()
        : await api.getDemands(cropFilter ? { crop: cropFilter } : {})
      setDemands(data)

      // Fetch buyer details for each unique buyer_id
      const ids = [...new Set(data.map(d => d.buyer_id))]
      const buyers = await Promise.all(ids.map(id =>
        api.listBuyers().then(list => list.find(b => b.id === id)).catch(() => null)
      ))
      const map = {}
      buyers.forEach(b => { if (b) map[b.id] = b })
      setBuyerMap(map)
    } catch (e) {
      setError(e.message)
      setDemands([])
    }
  }, [role, cropFilter])

  useEffect(() => { loadDemands() }, [loadDemands])

  async function handleCancel(id) {
    if (!window.confirm('Cancel this demand? This cannot be undone.')) return
    try {
      await api.cancelDemand(id)
      setToast('Demand cancelled.')
      loadDemands()
    } catch (e) {
      setError(e.message)
    }
  }

  function handleRespond(demand) {
    setRespondTo(demand)
  }

  function handleRespondDone(lot, offer) {
    setRespondTo(null)
    setToast(`Offer of ₹${offer.offered_price_per_kg}/kg for ${offer.quantity_kg.toLocaleString()} kg sent to the buyer using lot ${lot.lot_number}. You'll be notified if it's accepted.`)
    loadDemands()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <div>
          <h1 className="font-display text-3xl font-bold">🛒 Buyer Demands</h1>
          <p className="text-ink/60 dark:text-paper/60 text-sm mt-0.5">
            {role === 'buyer' ? 'Manage your buying requirements.' : 'Browse active buyer demands and respond with your crop lots.'}
          </p>
        </div>
        {role === 'buyer' && (
          <button onClick={() => setShowForm(s => !s)} className="bg-marigold hover:bg-amber-400 text-ink font-semibold rounded-lg px-4 py-2 text-sm">
            {showForm ? 'Close' : '+ Post Demand'}
          </button>
        )}
      </div>

      {toast && (
        <div className="mt-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-700 dark:text-emerald-300 text-sm rounded-lg px-3 py-2">
          {toast} <button onClick={() => setToast('')} className="ml-2 underline text-xs">Dismiss</button>
        </div>
      )}
      {error && (
        <div className="mt-3 bg-red-50 dark:bg-red-950/40 border border-red-200 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2">{error}</div>
      )}

      {showForm && role === 'buyer' && (
        <div className="mt-4">
          <CreateDemandForm
            onCreated={() => { setShowForm(false); setToast('Demand posted successfully.'); loadDemands() }}
            onClose={() => setShowForm(false)}
          />
        </div>
      )}

      {role === 'farmer' && (
        <div className="flex items-center gap-3 mt-4 mb-4 flex-wrap">
          <select value={cropFilter} onChange={e => setCropFilter(e.target.value)} className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper">
            <option value="">All crops</option>
            {CROPS.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
      )}

      {demands === null ? (
        <LoadingSpinner label="Loading demands…" />
      ) : demands.length === 0 ? (
        <div className="mt-6 text-sm text-ink/50 dark:text-paper/50">
          {role === 'buyer' ? 'No demands yet. Post your first buying requirement.' : 'No active buyer demands found.'}
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
          {demands.map(d => (
            <DemandCard
              key={d.id}
              demand={d}
              buyerMap={buyerMap}
              role={role}
              onRespond={handleRespond}
              onCancel={handleCancel}
            />
          ))}
        </div>
      )}

      {respondTo && (
        <RespondWithLotModal
          demand={respondTo}
          onDone={handleRespondDone}
          onClose={() => setRespondTo(null)}
        />
      )}
    </div>
  )
}
