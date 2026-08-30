import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const MAX_IMAGE_MB = 8
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']

function QualityImageUpload({ crop, grading, setGrading }) {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const inputRef = React.useRef(null)

  function handleFile(selected) {
    setUploadError('')
    setGrading(null)
    if (!selected) return
    if (!ALLOWED_TYPES.includes(selected.type)) {
      setUploadError('Please upload a JPG, PNG, or WEBP image.')
      return
    }
    if (selected.size > MAX_IMAGE_MB * 1024 * 1024) {
      setUploadError(`Image is too large (${(selected.size / 1_048_576).toFixed(1)} MB). Maximum is ${MAX_IMAGE_MB} MB.`)
      return
    }
    setFile(selected)
    setPreviewUrl(URL.createObjectURL(selected))
  }

  function removeImage() {
    setFile(null)
    setPreviewUrl(null)
    setGrading(null)
    setUploadError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  async function analyze() {
    if (!file) return
    setAnalyzing(true)
    setUploadError('')
    try {
      const res = await api.analyzeQualityImage(crop, file)
      setGrading(res)
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="border border-dashed border-black/15 rounded-xl p-4">
      <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-2">Crop photo (optional, for AI quality assessment)</label>
      {uploadError && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-xs rounded-lg px-3 py-2 mb-3">{uploadError}</div>}

      {!previewUrl ? (
        <label className="flex flex-col items-center justify-center gap-1.5 border-2 border-dashed border-black/10 dark:border-white/15 rounded-lg py-6 cursor-pointer hover:bg-wheat/40 transition-colors">
          <span className="text-2xl">📷</span>
          <span className="text-sm text-ink/60 dark:text-paper/60">Tap to upload a photo of your {crop}</span>
          <span className="text-xs text-ink/35 dark:text-paper/35">JPG, PNG, or WEBP -- up to {MAX_IMAGE_MB} MB</span>
          <input
            ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp"
            className="hidden" onChange={e => handleFile(e.target.files?.[0])}
          />
        </label>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4 items-start">
          <img src={previewUrl} alt={`Preview of uploaded ${crop} photo`} className="w-full sm:w-32 h-32 object-cover rounded-lg border border-black/10 dark:border-white/15" />
          <div className="flex-1 space-y-2">
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={analyze} disabled={analyzing} className="text-sm bg-forest text-paper rounded-lg px-4 py-2 font-medium disabled:opacity-60">
                {analyzing ? 'Analyzing photo...' : '🔍 Analyze this photo'}
              </button>
              <label className="text-sm bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg px-4 py-2 font-medium cursor-pointer hover:bg-wheat dark:bg-white/5">
                Replace
                <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={e => handleFile(e.target.files?.[0])} />
              </label>
              <button type="button" onClick={removeImage} className="text-sm text-red-500 dark:text-red-400 hover:underline px-2">Remove</button>
            </div>
            {grading && (
              <div className="text-sm bg-wheat/50 rounded-lg p-3 space-y-1">
                <div className="flex items-center gap-2">
                  <Badge tone="forest">Grade {grading.quality_grade}</Badge>
                  <span className="font-mono-data text-xs text-ink/60 dark:text-paper/60">{grading.visual_quality_score}% score</span>
                  {grading.demo_mode && <Badge tone="warning">Demo AI Assessment</Badge>}
                </div>
                <ul className="text-xs text-ink/60 dark:text-paper/60 list-disc list-inside space-y-0.5">
                  {grading.detected_notes.map((n, i) => <li key={i}>{n}</li>)}
                </ul>
                <p className="text-[11px] text-ink/40 dark:text-paper/40 italic">{grading.analysis_method}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function NewListingForm({ crops, onCreated, onClose }) {
  const [crop, setCrop] = useState('Tomato')
  const [quantity, setQuantity] = useState(1000)
  const [price, setPrice] = useState(20)
  const [availableDate, setAvailableDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [minPrice, setMinPrice] = useState('')
  const [grading, setGrading] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  function validate() {
    const errs = {}
    if (!quantity || quantity <= 0) errs.quantity = 'Quantity must be greater than 0 kg.'
    if (quantity > 100000) errs.quantity = 'Quantity seems unrealistically high -- please double-check.'
    if (!price || price <= 0) errs.price = 'Expected price must be greater than ₹0/kg.'
    if (minPrice && Number(minPrice) <= 0) errs.minPrice = 'Minimum acceptable price must be greater than ₹0/kg if set.'
    if (minPrice && Number(minPrice) > price) errs.minPrice = 'Minimum acceptable price cannot be higher than your expected price.'
    if (!availableDate) errs.availableDate = 'Please select an available-from date.'
    setFieldErrors(errs)
    return Object.keys(errs).length === 0
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!validate()) return
    setSubmitting(true)
    try {
      await api.createListing({
        crop, quantity_kg: quantity, expected_price_per_kg: price,
        available_date: availableDate,
        quality_grade: grading?.quality_grade || 'B',
        quality_score: grading?.visual_quality_score || 75,
        min_acceptable_price: minPrice ? Number(minPrice) : undefined,
      })
      onCreated()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={submit} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 mb-6 space-y-4">
      <h2 className="font-display font-semibold text-lg">Post your harvest</h2>
      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm rounded-lg px-3 py-2">{error}</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
          <select value={crop} onChange={e => { setCrop(e.target.value); setGrading(null) }} className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
            {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg)</label>
          <input type="number" min="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))} className={`w-full border rounded-lg px-3 py-2.5 text-sm ${fieldErrors.quantity ? 'border-red-400' : 'border-black/10 dark:border-white/15'}`} />
          {fieldErrors.quantity && <p className="text-xs text-red-600 mt-1">{fieldErrors.quantity}</p>}
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Expected price (₹/kg)</label>
          <input type="number" min="1" value={price} onChange={e => setPrice(Number(e.target.value))} className={`w-full border rounded-lg px-3 py-2.5 text-sm ${fieldErrors.price ? 'border-red-400' : 'border-black/10 dark:border-white/15'}`} />
          {fieldErrors.price && <p className="text-xs text-red-600 mt-1">{fieldErrors.price}</p>}
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Available from</label>
          <input type="date" value={availableDate} onChange={e => setAvailableDate(e.target.value)} className={`w-full border rounded-lg px-3 py-2.5 text-sm ${fieldErrors.availableDate ? 'border-red-400' : 'border-black/10 dark:border-white/15'}`} />
        </div>
      </div>
      <div>
        <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Minimum acceptable price (₹/kg, optional)</label>
        <input type="number" min="0" value={minPrice} onChange={e => setMinPrice(e.target.value)} placeholder="Offers below this will be rejected automatically" className={`w-full sm:w-64 border rounded-lg px-3 py-2.5 text-sm ${fieldErrors.minPrice ? 'border-red-400' : 'border-black/10 dark:border-white/15'}`} />
        {fieldErrors.minPrice && <p className="text-xs text-red-600 mt-1">{fieldErrors.minPrice}</p>}
      </div>

      <QualityImageUpload crop={crop} grading={grading} setGrading={setGrading} />

      <div className="flex items-center gap-3">
        <button disabled={submitting} className="bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg px-5 py-2.5 transition-colors disabled:opacity-60">
          {submitting ? 'Posting...' : 'Post listing'}
        </button>
        <button type="button" onClick={onClose} className="text-sm text-ink/50 dark:text-paper/50 hover:underline">Cancel</button>
      </div>
    </form>
  )
}

function OffersPanel({ listing, onChanged }) {
  const [offers, setOffers] = useState(null)
  const [matches, setMatches] = useState(null)
  const [matchError, setMatchError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null) // { id, type: 'accept'|'reject' }
  const [successMsg, setSuccessMsg] = useState('')

  useEffect(() => {
    api.offersForListing(listing.id).then(setOffers).catch(() => setOffers([]))
    api.matchBuyers(listing.id).then(r => setMatches(r.matches)).catch(e => { setMatches([]); setMatchError(e.message) })
  }, [listing.id])

  async function accept(id) {
    setBusyId(id)
    setConfirmAction(null)
    try {
      await api.acceptOffer(id)
      setSuccessMsg('Offer accepted -- the listing is now marked sold.')
      onChanged()
    } catch (e) {
      setSuccessMsg('')
      setMatchError(e.message)
    } finally {
      setBusyId(null)
    }
  }
  async function reject(id) {
    setBusyId(id)
    setConfirmAction(null)
    try {
      await api.rejectOffer(id)
      setSuccessMsg('Offer rejected.')
      const fresh = await api.offersForListing(listing.id)
      setOffers(fresh)
    } catch (e) {
      setMatchError(e.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="bg-wheat/50 rounded-xl p-4 mt-3 space-y-4">
      {successMsg && <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-700 dark:text-emerald-300 text-xs rounded-lg px-3 py-2">{successMsg}</div>}
      {matchError && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-xs rounded-lg px-3 py-2">{matchError}</div>}

      {confirmAction && (
        <div className="bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg p-3 text-sm space-y-2">
          <p>Are you sure you want to <strong>{confirmAction.type}</strong> this offer? This cannot be undone.</p>
          <div className="flex gap-2">
            <button
              onClick={() => confirmAction.type === 'accept' ? accept(confirmAction.id) : reject(confirmAction.id)}
              className={`text-xs rounded-lg px-3 py-1.5 font-semibold text-paper ${confirmAction.type === 'accept' ? 'bg-forest' : 'bg-red-500'}`}
            >
              Yes, {confirmAction.type}
            </button>
            <button onClick={() => setConfirmAction(null)} className="text-xs bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg px-3 py-1.5 font-semibold">Cancel</button>
          </div>
        </div>
      )}

      <div>
        <h4 className="text-sm font-semibold mb-2">Offers received {offers ? `(${offers.length})` : ''}</h4>
        {offers === null ? <p className="text-xs text-ink/50 dark:text-paper/50">Loading...</p> : offers.length === 0 ? (
          <p className="text-xs text-ink/50 dark:text-paper/50">No offers yet -- check back soon, or share this listing directly with a buyer.</p>
        ) : (
          <div className="space-y-2">
            {offers.map(o => (
              <div key={o.id} className="flex items-center justify-between bg-white dark:bg-white/5 rounded-lg px-3 py-2 text-sm">
                <div>
                  <div className="font-medium">₹{o.offered_price_per_kg}/kg · {o.quantity_kg.toLocaleString()} kg</div>
                  {o.message && <div className="text-xs text-ink/50 dark:text-paper/50">"{o.message}"</div>}
                </div>
                {o.status === 'pending' ? (
                  <div className="flex gap-2">
                    <button disabled={busyId === o.id} onClick={() => setConfirmAction({ id: o.id, type: 'accept' })} className="text-xs bg-forest text-paper rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">
                      {busyId === o.id ? 'Working...' : 'Accept'}
                    </button>
                    <button disabled={busyId === o.id} onClick={() => setConfirmAction({ id: o.id, type: 'reject' })} className="text-xs bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">
                      Reject
                    </button>
                  </div>
                ) : <Badge tone={o.status === 'accepted' ? 'success' : 'neutral'}>{o.status}</Badge>}
              </div>
            ))}
          </div>
        )}
      </div>
      <div>
        <h4 className="text-sm font-semibold mb-2">⭐ Smart buyer matches</h4>
        {matches === null ? <p className="text-xs text-ink/50 dark:text-paper/50">Loading...</p> : matches.length === 0 ? (
          <p className="text-xs text-ink/50 dark:text-paper/50">No buyer matches found for this listing yet.</p>
        ) : (
          <div className="space-y-2">
            {matches.map(m => (
              <div key={m.buyer_id} className="bg-white dark:bg-white/5 rounded-lg px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">#{m.rank} {m.company_name}</span>
                  <span className="font-mono-data font-semibold text-forest">{m.match_score}% match</span>
                </div>
                <div className="text-xs text-ink/50 dark:text-paper/50">{m.reasons.join(' · ')}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function MakeOfferForm({ listing, onDone }) {
  const [price, setPrice] = useState(listing.expected_price_per_kg)
  const [qty, setQty] = useState(listing.quantity_kg)
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [confirming, setConfirming] = useState(false)

  function validate() {
    const errs = {}
    if (!price || price <= 0) errs.price = 'Offer price must be greater than ₹0/kg.'
    if (!qty || qty <= 0) errs.qty = 'Quantity must be greater than 0 kg.'
    if (qty > listing.quantity_kg) errs.qty = `Quantity cannot exceed the listed ${listing.quantity_kg.toLocaleString()} kg.`
    setFieldErrors(errs)
    return Object.keys(errs).length === 0
  }

  function handleSubmitClick(e) {
    e.preventDefault()
    setError('')
    if (!validate()) return
    setConfirming(true)
  }

  async function confirmSubmit() {
    setConfirming(false)
    setSubmitting(true)
    setError('')
    try {
      await api.createOffer({ listing_id: listing.id, offered_price_per_kg: price, quantity_kg: qty, message })
      onDone()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmitClick} className="bg-wheat/50 rounded-xl p-4 mt-3 space-y-3">
      {error && <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-xs rounded-lg px-3 py-2">{error}</div>}
      {confirming && (
        <div className="bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg p-3 text-sm space-y-2">
          <p>Send an offer of <strong>₹{price}/kg</strong> for <strong>{qty.toLocaleString()} kg</strong>?</p>
          <div className="flex gap-2">
            <button type="button" onClick={confirmSubmit} disabled={submitting} className="text-xs bg-forest text-paper rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">
              {submitting ? 'Sending...' : 'Yes, send offer'}
            </button>
            <button type="button" onClick={() => setConfirming(false)} className="text-xs bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg px-3 py-1.5 font-semibold">Cancel</button>
          </div>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Your offer (₹/kg)</label>
          <input type="number" value={price} onChange={e => setPrice(Number(e.target.value))} className={`w-full border rounded-lg px-3 py-2 text-sm ${fieldErrors.price ? 'border-red-400' : 'border-black/10 dark:border-white/15'}`} />
          {fieldErrors.price && <p className="text-xs text-red-600 mt-1">{fieldErrors.price}</p>}
        </div>
        <div>
          <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg)</label>
          <input type="number" value={qty} onChange={e => setQty(Number(e.target.value))} max={listing.quantity_kg} className={`w-full border rounded-lg px-3 py-2 text-sm ${fieldErrors.qty ? 'border-red-400' : 'border-black/10 dark:border-white/15'}`} />
          {fieldErrors.qty && <p className="text-xs text-red-600 mt-1">{fieldErrors.qty}</p>}
        </div>
      </div>

      <input value={message} onChange={e => setMessage(e.target.value)} placeholder="Message to farmer (optional)" className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
      <button disabled={submitting} className="bg-forest text-paper text-sm font-semibold rounded-lg px-4 py-2 disabled:opacity-60">
        {submitting ? 'Sending...' : 'Send offer'}
      </button>
    </form>
  )
}

export default function Marketplace() {
  const { role } = useAuth()
  const [crops, setCrops] = useState([])
  const [listings, setListings] = useState(null)
  const [cropFilter, setCropFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [scope, setScope] = useState('all') // all | mine

  useEffect(() => { api.getCrops().then(setCrops) }, [])

  async function loadListings() {
    setListings(null)
    try {
      const data = scope === 'mine' && role === 'farmer'
        ? await api.myListings()
        : await api.getListings(cropFilter ? { crop: cropFilter } : {})
      setListings(data)
    } catch (e) {
      setListings([])
    }
  }

  useEffect(() => { loadListings() }, [cropFilter, scope]) // eslint-disable-line

  return (
    <div>
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="font-display text-3xl font-bold">🌾 AgriMarket</h1>
        {role === 'farmer' && (
          <button onClick={() => setShowForm(s => !s)} className="bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg px-4 py-2 text-sm transition-colors">
            {showForm ? 'Close form' : '+ Post harvest'}
          </button>
        )}
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-6">Post produce, receive competing offers, and connect directly with buyers.</p>

      {showForm && role === 'farmer' && (
        <NewListingForm crops={crops} onCreated={() => { setShowForm(false); setScope('mine'); loadListings() }} onClose={() => setShowForm(false)} />
      )}

      <div className="flex flex-wrap items-center gap-3 mb-6">
        {role === 'farmer' && (
          <div className="flex bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg p-1 text-sm">
            <button onClick={() => setScope('all')} className={`px-3 py-1.5 rounded-md font-medium ${scope === 'all' ? 'bg-forest text-paper' : 'text-ink/60 dark:text-paper/60'}`}>All listings</button>
            <button onClick={() => setScope('mine')} className={`px-3 py-1.5 rounded-md font-medium ${scope === 'mine' ? 'bg-forest text-paper' : 'text-ink/60 dark:text-paper/60'}`}>My listings</button>
          </div>
        )}
        <select value={cropFilter} onChange={e => setCropFilter(e.target.value)} className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm">
          <option value="">All crops</option>
          {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
        </select>
      </div>

      {listings === null ? <LoadingSpinner label="Loading listings..." /> : listings.length === 0 ? (
        <p className="text-sm text-ink/50 dark:text-paper/50">No listings found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {listings.map(l => (
            <div key={l.id} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-display font-semibold text-lg">{l.crop}</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50">{l.location} · Available {l.available_date}</div>
                </div>
                <Badge tone={l.status === 'active' ? 'success' : l.status === 'sold' ? 'forest' : 'neutral'}>{l.status}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-2 text-sm mb-3">
                <div><div className="text-xs text-ink/40 dark:text-paper/40">Quantity</div><div className="font-mono-data font-semibold">{l.quantity_kg.toLocaleString()} kg</div></div>
                <div><div className="text-xs text-ink/40 dark:text-paper/40">Grade</div><div className="font-semibold">{l.quality_grade} ({l.quality_score}%)</div></div>
                <div><div className="text-xs text-ink/40 dark:text-paper/40">Expected</div><div className="font-mono-data font-semibold">₹{l.expected_price_per_kg}/kg</div></div>
              </div>

              {role === 'buyer' && l.status === 'active' && (
                expandedId === l.id ? <MakeOfferForm listing={l} onDone={() => { setExpandedId(null); loadListings() }} /> : (
                  <button onClick={() => setExpandedId(l.id)} className="text-sm bg-forest text-paper font-semibold rounded-lg px-4 py-2">Make an offer</button>
                )
              )}

              {role === 'farmer' && scope === 'mine' && (
                <button onClick={() => setExpandedId(expandedId === l.id ? null : l.id)} className="text-sm text-forest font-semibold hover:underline">
                  {expandedId === l.id ? 'Hide offers & matches' : 'View offers & buyer matches →'}
                </button>
              )}
              {role === 'farmer' && scope === 'mine' && expandedId === l.id && (
                <OffersPanel listing={l} onChanged={loadListings} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
