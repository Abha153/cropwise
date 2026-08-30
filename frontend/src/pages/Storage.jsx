import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import Badge from '../components/Badge'

const TYPE_LABELS = {
  WAREHOUSE: '🏭 Warehouse',
  COLD_STORAGE: '❄️ Cold Storage',
  FPO_STORAGE: '🤝 FPO Storage',
  PRIVATE_STORAGE: '🔒 Private Storage',
  GOVERNMENT_STORAGE: '🏛️ Government Storage',
}

const TYPE_COLORS = {
  WAREHOUSE: 'blue',
  COLD_STORAGE: 'purple',
  FPO_STORAGE: 'green',
  PRIVATE_STORAGE: 'orange',
  GOVERNMENT_STORAGE: 'red',
}

const BOOKING_STATUS_COLORS = {
  REQUESTED: 'blue',
  CONFIRMED: 'green',
  ACTIVE: 'purple',
  COMPLETED: 'gray',
  CANCELLED: 'red',
}

export default function Storage() {
  const { user, role } = useAuth()
  const [facilities, setFacilities] = useState([])
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('browse') // browse | my-bookings
  const [cropFilter, setCropFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [selectedFacility, setSelectedFacility] = useState(null)
  const [showBookingForm, setShowBookingForm] = useState(false)
  const [bookingForm, setBookingForm] = useState({
    quantity_kg: '',
    start_date: '',
    end_date: '',
    lot_id: '',
  })
  const [estimatedCost, setEstimatedCost] = useState(null)
  const [booking, setBooking] = useState(false)
  const [bookingSuccess, setBookingSuccess] = useState('')
  const [crops, setCrops] = useState([])

  useEffect(() => {
    api.getCrops().then(setCrops).catch(() => {})
    loadFacilities()
    if (role === 'farmer') loadBookings()
  }, [role])

  async function loadFacilities() {
    setLoading(true)
    try {
      const params = {}
      if (cropFilter) params.crop = cropFilter
      if (typeFilter) params.facility_type = typeFilter
      const data = await api.getStorageFacilities(params)
      setFacilities(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function loadBookings() {
    try {
      const data = await api.myStorageBookings()
      setBookings(data)
    } catch (e) {}
  }

  async function estimateCost() {
    if (!selectedFacility || !bookingForm.quantity_kg || !bookingForm.start_date || !bookingForm.end_date) return
    try {
      const start = new Date(bookingForm.start_date)
      const end = new Date(bookingForm.end_date)
      const days = Math.max(Math.ceil((end - start) / (1000 * 60 * 60 * 24)), 1)
      const data = await api.estimateStorageCost(selectedFacility.id, bookingForm.quantity_kg, days)
      setEstimatedCost(data)
    } catch (e) {}
  }

  async function submitBooking(e) {
    e.preventDefault()
    if (!selectedFacility) return
    setBooking(true)
    try {
      await api.createStorageBooking({
        storage_facility_id: selectedFacility.id,
        quantity_kg: parseFloat(bookingForm.quantity_kg),
        start_date: bookingForm.start_date,
        end_date: bookingForm.end_date || null,
        lot_id: bookingForm.lot_id ? parseInt(bookingForm.lot_id) : null,
      })
      setBookingSuccess(`Storage booking requested at ${selectedFacility.name}!`)
      setShowBookingForm(false)
      setSelectedFacility(null)
      loadBookings()
      setActiveTab('my-bookings')
    } catch (e) {
      setError(e.message)
    } finally {
      setBooking(false)
    }
  }

  async function cancelBooking(id) {
    if (!window.confirm('Cancel this storage booking?')) return
    try {
      await api.cancelStorageBooking(id)
      loadBookings()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">🏭 Storage Marketplace</h1>
      <p className="text-ink/60 dark:text-paper/60 mb-1">Find and book nearby storage facilities for your crops.</p>
      <p className="text-xs text-amber-600 dark:text-amber-400 mb-6">
        ⚠️ Demo facilities — availability and pricing are illustrative only, not real-time government or verified warehouse data.
      </p>

      {bookingSuccess && (
        <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 rounded-lg text-emerald-700 dark:text-emerald-300 text-sm">
          ✅ {bookingSuccess}
        </div>
      )}

      {/* Tabs */}
      {role === 'farmer' && (
        <div className="flex gap-2 mb-6">
          {['browse', 'my-bookings'].map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? 'bg-forest text-paper'
                  : 'bg-white dark:bg-white/5 border border-black/10 dark:border-white/10 text-ink/70 dark:text-paper/70 hover:bg-black/5'
              }`}>
              {tab === 'browse' ? '🔍 Browse Storage' : '📋 My Bookings'}
            </button>
          ))}
        </div>
      )}

      {activeTab === 'browse' && (
        <>
          {/* Filters */}
          <div className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-4 mb-6 flex flex-wrap gap-3 items-end">
            <div>
              <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Crop</label>
              <select value={cropFilter} onChange={e => setCropFilter(e.target.value)}
                className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper">
                <option value="">All crops</option>
                {crops.map(c => <option key={c.name} value={c.name}>{c.emoji} {c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Type</label>
              <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
                className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper">
                <option value="">All types</option>
                {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <button onClick={loadFacilities}
              className="bg-forest text-paper px-4 py-2 rounded-lg text-sm font-semibold hover:bg-forest/90">
              Search
            </button>
          </div>

          {loading ? <LoadingSpinner /> : error ? (
            <div className="text-red-500 text-sm">{error}</div>
          ) : facilities.length === 0 ? (
            <div className="text-center py-12 text-ink/40 dark:text-paper/40">
              <p className="text-4xl mb-3">🏭</p>
              <p className="font-medium">No storage facilities found</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {facilities.map(f => (
                <div key={f.id} className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-5 shadow-card hover:shadow-lg transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-ink dark:text-paper">{f.name}</h3>
                      <p className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">📍 {f.location}</p>
                    </div>
                    <Badge color={TYPE_COLORS[f.facility_type] || 'gray'} size="sm">
                      {TYPE_LABELS[f.facility_type] || f.facility_type}
                    </Badge>
                  </div>

                  {f.is_demo && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">⚠️ Demo Facility</p>
                  )}

                  <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                    <div className="bg-black/3 dark:bg-white/5 rounded-lg p-2">
                      <p className="text-xs text-ink/50 dark:text-paper/50">Total capacity</p>
                      <p className="font-semibold">{(f.capacity_kg / 1000).toFixed(0)}t</p>
                    </div>
                    <div className="bg-black/3 dark:bg-white/5 rounded-lg p-2">
                      <p className="text-xs text-ink/50 dark:text-paper/50">Available</p>
                      <p className="font-semibold text-emerald-600">{(f.available_capacity_kg / 1000).toFixed(0)}t</p>
                    </div>
                    <div className="bg-black/3 dark:bg-white/5 rounded-lg p-2">
                      <p className="text-xs text-ink/50 dark:text-paper/50">Rate</p>
                      <p className="font-semibold">₹{f.price_per_kg_per_day}/kg/day</p>
                    </div>
                    <div className="bg-black/3 dark:bg-white/5 rounded-lg p-2">
                      <p className="text-xs text-ink/50 dark:text-paper/50">Utilised</p>
                      <p className="font-semibold">{f.utilisation_pct}%</p>
                    </div>
                  </div>

                  {/* Utilisation bar */}
                  <div className="mb-3">
                    <div className="h-1.5 bg-black/10 dark:bg-white/10 rounded-full overflow-hidden">
                      <div className="h-full bg-forest rounded-full" style={{ width: `${f.utilisation_pct}%` }} />
                    </div>
                  </div>

                  {f.temperature_controlled && (
                    <p className="text-xs text-blue-600 dark:text-blue-400 mb-2">❄️ Temperature Controlled</p>
                  )}

                  {f.crop_types?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {f.crop_types.slice(0, 4).map(c => (
                        <span key={c} className="text-xs bg-forest/10 text-forest px-2 py-0.5 rounded-full">{c}</span>
                      ))}
                      {f.crop_types.length > 4 && <span className="text-xs text-ink/40">+{f.crop_types.length - 4}</span>}
                    </div>
                  )}

                  {role === 'farmer' && (
                    <button
                      onClick={() => { setSelectedFacility(f); setShowBookingForm(true); setEstimatedCost(null) }}
                      className="w-full mt-2 bg-forest text-paper py-2 rounded-lg text-sm font-semibold hover:bg-forest/90 transition-colors">
                      Book Storage
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'my-bookings' && role === 'farmer' && (
        bookings.length === 0 ? (
          <div className="text-center py-12 text-ink/40 dark:text-paper/40">
            <p className="text-4xl mb-3">📋</p>
            <p className="font-medium">No storage bookings yet</p>
            <button onClick={() => setActiveTab('browse')}
              className="mt-3 text-forest font-semibold text-sm">Browse storage facilities →</button>
          </div>
        ) : (
          <div className="space-y-4">
            {bookings.map(b => (
              <div key={b.id} className="bg-white dark:bg-white/5 rounded-2xl border border-black/5 dark:border-white/10 p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold">{b.facility_name || 'Storage Facility'}</h3>
                    <p className="text-xs text-ink/50 dark:text-paper/50">{b.facility_location} • {b.facility_type}</p>
                    {b.is_demo_facility && <p className="text-xs text-amber-500">⚠️ Demo Facility</p>}
                  </div>
                  <Badge color={BOOKING_STATUS_COLORS[b.status] || 'gray'} size="sm">{b.status}</Badge>
                </div>
                <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                  <div><p className="text-xs text-ink/50 dark:text-paper/50">Quantity</p><p className="font-semibold">{b.quantity_kg} kg</p></div>
                  <div><p className="text-xs text-ink/50 dark:text-paper/50">From</p><p className="font-semibold">{b.start_date}</p></div>
                  <div><p className="text-xs text-ink/50 dark:text-paper/50">To</p><p className="font-semibold">{b.end_date || '—'}</p></div>
                  <div><p className="text-xs text-ink/50 dark:text-paper/50">Est. Cost</p><p className="font-semibold">{b.estimated_cost ? `₹${b.estimated_cost.toLocaleString('en-IN')}` : '—'}</p></div>
                </div>
                {['REQUESTED', 'CONFIRMED'].includes(b.status) && (
                  <button onClick={() => cancelBooking(b.id)}
                    className="mt-3 text-red-500 text-xs font-semibold hover:underline">
                    Cancel Booking
                  </button>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {/* Booking Modal */}
      {showBookingForm && selectedFacility && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="font-bold text-xl mb-1">Book Storage</h3>
            <p className="text-ink/60 dark:text-paper/60 text-sm mb-4">{selectedFacility.name} — {selectedFacility.location}</p>

            {selectedFacility.is_demo && (
              <p className="text-xs text-amber-600 mb-4 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                ⚠️ Demo Facility — this booking is for demonstration purposes only.
              </p>
            )}

            <form onSubmit={submitBooking} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Quantity (kg) *</label>
                <input type="number" min="1" max={selectedFacility.available_capacity_kg}
                  value={bookingForm.quantity_kg} onChange={e => setBookingForm(f => ({ ...f, quantity_kg: e.target.value }))}
                  required className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
                <p className="text-xs text-ink/40 mt-0.5">Available: {selectedFacility.available_capacity_kg.toLocaleString('en-IN')} kg</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Start Date *</label>
                  <input type="date" value={bookingForm.start_date}
                    onChange={e => setBookingForm(f => ({ ...f, start_date: e.target.value }))}
                    required className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">End Date</label>
                  <input type="date" value={bookingForm.end_date}
                    onChange={e => setBookingForm(f => ({ ...f, end_date: e.target.value }))}
                    className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1">Lot ID (optional)</label>
                <input type="number" value={bookingForm.lot_id}
                  onChange={e => setBookingForm(f => ({ ...f, lot_id: e.target.value }))}
                  placeholder="Link to a lot"
                  className="w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper" />
              </div>

              {bookingForm.quantity_kg && bookingForm.start_date && bookingForm.end_date && (
                <button type="button" onClick={estimateCost}
                  className="text-forest text-sm font-semibold hover:underline">
                  Calculate estimated cost
                </button>
              )}

              {estimatedCost && (
                <div className="p-3 bg-forest/10 rounded-lg text-sm">
                  <p className="font-semibold text-forest">Estimated Cost: ₹{estimatedCost.estimated_cost?.toLocaleString('en-IN')}</p>
                  <p className="text-xs text-ink/50 dark:text-paper/50">
                    {estimatedCost.quantity_kg} kg × ₹{estimatedCost.price_per_kg_per_day}/kg/day × {estimatedCost.days} days
                  </p>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => { setShowBookingForm(false); setSelectedFacility(null) }}
                  className="flex-1 border border-black/10 dark:border-white/15 py-2 rounded-lg text-sm font-semibold">
                  Cancel
                </button>
                <button type="submit" disabled={booking}
                  className="flex-1 bg-forest text-paper py-2 rounded-lg text-sm font-semibold disabled:opacity-60">
                  {booking ? 'Booking...' : 'Request Booking'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
