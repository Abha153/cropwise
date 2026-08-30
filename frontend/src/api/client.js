const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('cropwise_token')
}

async function request(path, { method = 'GET', body, auth = false, form = false, token = null } = {}) {
  const headers = {}
  if (!form) headers['Content-Type'] = 'application/json'
  if (auth) {
    const t = token || getToken()
    if (t) headers['Authorization'] = `Bearer ${t}`
  }
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: form ? body : body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const errJson = await res.json()
      detail = errJson.detail || detail
    } catch (e) {}
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Auth
  loginFarmer: (email, password) => {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    return request('/auth/login', { method: 'POST', body: form, form: true })
  },
  registerFarmer: (payload) => request('/auth/register/farmer', { method: 'POST', body: payload }),
  registerBuyer: (payload) => request('/auth/register/buyer', { method: 'POST', body: payload }),
  me: () => request('/auth/me', { auth: true }),

  // Market
  getCrops: () => request('/market/crops'),
  getMarkets: () => request('/market/markets'),
  getPrices: (crop, market, days = 30, includeDemo = false) => request(`/market/prices?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}&days=${days}&include_demo=${includeDemo}`),
  compareMarkets: (crop, quantityKg, location) => request(`/market/compare?crop=${encodeURIComponent(crop)}&quantity_kg=${quantityKg}&location=${encodeURIComponent(location)}`),
  getLiveMarkets: (state = 'Chhattisgarh') => request(`/market/live-markets?state=${encodeURIComponent(state)}`),

  // Advisor
  advisorRecommend: (payload) => request('/advisor/recommend', { method: 'POST', body: payload }),

  // Forecast
  getForecast: (crop, market, includeDemo = false) => request(`/forecast?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}&include_demo=${includeDemo}`),

  // Listings
  createListing: (payload) => request('/listings', { method: 'POST', body: payload, auth: true }),
  getListings: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/listings${qs ? `?${qs}` : ''}`)
  },
  myListings: () => request('/listings/mine', { auth: true }),
  getListing: (id) => request(`/listings/${id}`),
  updateListingStatus: (id, status) => request(`/listings/${id}/status?new_status=${status}`, { method: 'PATCH', auth: true }),
  deleteListing: (id) => request(`/listings/${id}`, { method: 'DELETE', auth: true }),

  // Offers
  createOffer: (payload) => request('/offers', { method: 'POST', body: payload, auth: true }),
  offersForListing: (listingId) => request(`/offers/listing/${listingId}`, { auth: true }),
  offersForLot: (lotId) => request(`/offers/lot/${lotId}`, { auth: true }),
  myOffers: () => request('/offers/mine', { auth: true }),
  acceptOffer: (id) => request(`/offers/${id}/accept`, { method: 'PATCH', auth: true }),
  rejectOffer: (id) => request(`/offers/${id}/reject`, { method: 'PATCH', auth: true }),

  // Matching
  matchBuyers: (listingId) => request(`/matching/listing/${listingId}`, { auth: true }),
  matchBuyersForLot: (lotId, topN = 5) => request(`/matching/lot/${lotId}?top_n=${topN}`, { auth: true }),

  // Logistics
  getVehicles: () => request('/logistics/vehicles'),
  farmPool: (payload) => request('/logistics/farmpool', { method: 'POST', body: payload }),

  // Profit
  profitSimulate: (payload) => request('/profit/simulate', { method: 'POST', body: payload }),
  profitCompare: (payload) => request('/profit/compare', { method: 'POST', body: payload }),

  // Group selling
  getGroupPools: (crop) => request(`/group-selling${crop ? `?crop=${encodeURIComponent(crop)}` : ''}`),
  joinGroupPool: (payload) => request('/group-selling/join', { method: 'POST', body: payload, auth: true }),

  // Notifications
  myNotifications: () => request('/notifications/mine', { auth: true }),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: 'PATCH', auth: true }),
  generateNotification: () => request('/notifications/generate', { method: 'POST', auth: true }),

  // Quality
  gradeQuality: (payload) => request('/quality/grade', { method: 'POST', body: payload }),
  analyzeQualityImage: (crop, file) => {
    const formData = new FormData()
    formData.append('crop', crop)
    formData.append('image', file)
    return request('/quality/analyze', { method: 'POST', body: formData, form: true })
  },

  // Assistant
  askAssistant: (payload) => request('/assistant/ask', { method: 'POST', body: payload }),
  assistantLanguages: () => request('/assistant/languages'),

  // Admin
  getImpact: (adminToken) => request('/admin/impact', { auth: true, token: adminToken }),
  getUserActivity: (adminToken) => request('/admin/user-activity', { auth: true, token: adminToken }),
  getRecentActivity: (adminToken, limit = 20) => request(`/admin/recent-activity?limit=${limit}`, { auth: true, token: adminToken }),
  getAdminUsers: (adminToken, { role, q } = {}) => {
    const params = new URLSearchParams()
    if (role) params.set('role', role)
    if (q) params.set('q', q)
    const qs = params.toString()
    return request(`/admin/users${qs ? `?${qs}` : ''}`, { auth: true, token: adminToken })
  },
  adminLogin: (username, password) => {
    const form = new URLSearchParams()
    form.set('username', username)
    form.set('password', password)
    return request('/auth/admin/login', { method: 'POST', body: form, form: true })
  },
  getDataSourceStatus: () => request('/market/data-source-status'),

  // Farmers/Buyers
  updateFarmerProfile: (payload) => request('/farmers/me', { method: 'PUT', body: payload, auth: true }),
  listBuyers: (crop) => request(`/buyers${crop ? `?crop=${encodeURIComponent(crop)}` : ''}`),

  // Lots (Phase 4)
  createLot: (payload) => request('/lots', { method: 'POST', body: payload, auth: true }),
  getLots: (params = {}) => { const qs = new URLSearchParams(params).toString(); return request(`/lots${qs ? `?${qs}` : ''}`) },
  myLots: () => request('/lots/mine', { auth: true }),
  getLot: (id) => request(`/lots/${id}`),
  updateLot: (id, payload) => request(`/lots/${id}`, { method: 'PATCH', body: payload, auth: true }),
  cancelLot: (id) => request(`/lots/${id}`, { method: 'DELETE', auth: true }),

  // Buyer Demands (Phase 1)
  createDemand: (payload) => request('/buyer-demands', { method: 'POST', body: payload, auth: true }),
  getDemands: (params = {}) => { const qs = new URLSearchParams(params).toString(); return request(`/buyer-demands${qs ? `?${qs}` : ''}`) },
  myDemands: () => request('/buyer-demands/mine', { auth: true }),
  getDemand: (id) => request(`/buyer-demands/${id}`),
  updateDemand: (id, payload) => request(`/buyer-demands/${id}`, { method: 'PATCH', body: payload, auth: true }),
  cancelDemand: (id) => request(`/buyer-demands/${id}/cancel`, { method: 'PATCH', auth: true }),
  demandMatches: (id) => request(`/buyer-demands/${id}/matches`, { auth: true }),

  // Buyer Verification (Phase 2)
  submitVerification: (payload) => request('/buyer-verification', { method: 'POST', body: payload, auth: true }),
  myVerification: () => request('/buyer-verification/me', { auth: true }),
  getBuyerVerification: (buyerId) => request(`/buyer-verification/${buyerId}`),
  adminListVerifications: (status = 'UNDER_REVIEW') => request(`/buyer-verification?status=${status}`, { auth: true }),
  adminApproveVerification: (buyerId, notes = '') => request(`/buyer-verification/${buyerId}/approve?notes=${encodeURIComponent(notes)}`, { method: 'PATCH', auth: true }),
  adminRejectVerification: (buyerId, reason) => request(`/buyer-verification/${buyerId}/reject?reason=${encodeURIComponent(reason)}`, { method: 'PATCH', auth: true }),

  // Transactions (Phase 10)
  myTransactions: () => request('/transactions/mine', { auth: true }),
  getTransaction: (id) => request(`/transactions/${id}`, { auth: true }),
  getTransactionTimeline: (id) => request(`/transactions/${id}/timeline`, { auth: true }),
  updateTransactionStatus: (id, status) => request(`/transactions/${id}/status`, { method: 'PATCH', body: { status }, auth: true }),
  adminListTransactions: (params = {}) => { const qs = new URLSearchParams(params).toString(); return request(`/transactions${qs ? `?${qs}` : ''}`, { auth: true }) },

  // Payments (Phase 11)
  myPayments: () => request('/payments/mine', { auth: true }),
  paymentForTransaction: (txnId) => request(`/payments/transaction/${txnId}`, { auth: true }),
  createPayment: (payload) => request('/payments', { method: 'POST', body: payload, auth: true }),
  initiatePayment: (id, method = 'UPI') => request(`/payments/${id}/initiate?payment_method=${encodeURIComponent(method)}`, { method: 'PATCH', auth: true }),
  confirmPaymentReceived: (id) => request(`/payments/${id}/confirm-received`, { method: 'PATCH', auth: true }),
  completeTransaction: (id) => request(`/payments/${id}/complete-transaction`, { method: 'PATCH', auth: true }),

  // Grievances (Phase 13)
  raiseGrievance: (payload) => request('/grievances', { method: 'POST', body: payload, auth: true }),
  myGrievances: () => request('/grievances/mine', { auth: true }),
  getGrievance: (id) => request(`/grievances/${id}`, { auth: true }),
  updateGrievance: (id, payload) => request(`/grievances/${id}`, { method: 'PATCH', body: payload, auth: true }),
  adminListGrievances: (params = {}) => { const qs = new URLSearchParams(params).toString(); return request(`/grievances${qs ? `?${qs}` : ''}`, { auth: true }) },

  // Storage (Phase 6)
  getStorageFacilities: (params = {}) => { const qs = new URLSearchParams(params).toString(); return request(`/storage/facilities${qs ? `?${qs}` : ''}`) },
  getStorageFacility: (id) => request(`/storage/facilities/${id}`),
  estimateStorageCost: (facilityId, quantityKg, days) => request(`/storage/estimate?facility_id=${facilityId}&quantity_kg=${quantityKg}&days=${days}`),
  createStorageBooking: (payload) => request('/storage/bookings', { method: 'POST', body: payload, auth: true }),
  myStorageBookings: () => request('/storage/bookings/mine', { auth: true }),
  getStorageBooking: (id) => request(`/storage/bookings/${id}`, { auth: true }),
  cancelStorageBooking: (id) => request(`/storage/bookings/${id}/cancel`, { method: 'PATCH', auth: true }),

  // Transport (Phase 9)
  createTransportRequest: (payload) => request('/transport/requests', { method: 'POST', body: payload, auth: true }),
  myTransportRequests: () => request('/transport/requests/mine', { auth: true }),
  getTransportRequest: (id) => request(`/transport/requests/${id}`, { auth: true }),
  updateTransportStatus: (id, status, extra = {}) => request(`/transport/requests/${id}/status`, { method: 'PATCH', body: { status, ...extra }, auth: true }),
  cancelTransportRequest: (id) => request(`/transport/requests/${id}/cancel`, { method: 'PATCH', auth: true }),
  getVehicleOptions: (quantityKg) => request(`/transport/vehicle-options${quantityKg ? `?quantity_kg=${quantityKg}` : ''}`),

  // Ratings (Phase 14)
  rateAsBuyer: (payload) => request('/ratings/buyer-rates-farmer', { method: 'POST', body: payload, auth: true }),
  rateAsFarmer: (payload) => request('/ratings/farmer-rates-buyer', { method: 'POST', body: payload, auth: true }),
  ratingsForBuyer: (buyerId) => request(`/ratings/for-buyer/${buyerId}`),
  ratingsForFarmer: (farmerId) => request(`/ratings/for-farmer/${farmerId}`),
  myTransactionRating: (transactionId) => request(`/ratings/my-transaction/${transactionId}`, { auth: true }),

  // Arrivals + Selling Window (Phase 7 & 8)
  getArrivals: (crop, market, days = 14) => request(`/market/arrivals?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}&days=${days}`),
  getSellingWindow: (crop, market, quantityKg, storageCostPerKgPerDay = 0.05) =>
    request(`/market/selling-window?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}&quantity_kg=${quantityKg}&storage_cost_per_kg_per_day=${storageCostPerKgPerDay}`),

  // Buyer notifications (Phase 16)
  myBuyerNotifications: () => request('/notifications/buyer/mine', { auth: true }),
  markBuyerNotificationRead: (id) => request(`/notifications/buyer/${id}/read`, { method: 'PATCH', auth: true }),
  generateBuyerAlert: () => request('/notifications/buyer/generate', { method: 'POST', auth: true }),
}

export { API_BASE_URL, getToken }
