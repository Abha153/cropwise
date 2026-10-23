// Remembers the last location the user EXPLICITLY chose on the weather page
// (picked from search results or via "Use My Location"), on this device only
// (localStorage). Privacy: coordinates are rounded to 2 decimals (~1 km --
// the same precision the weather provider is queried with), nothing is sent
// anywhere from here, and nothing is stored until the user picks a place.

const KEY = 'cropwise.weatherLocation.v1'
const CROP_KEY = 'cropwise.weatherCrop.v1'

export function roundCoord(n) {
  return Math.round(Number(n) * 100) / 100
}

export function isValidLocation(loc) {
  return !!loc && typeof loc === 'object'
    && Number.isFinite(loc.latitude) && Number.isFinite(loc.longitude)
    && Math.abs(loc.latitude) <= 90 && Math.abs(loc.longitude) <= 180
    && typeof loc.label === 'string' && loc.label.length > 0
}

export function loadLocation(storage = globalThis.localStorage) {
  try {
    const raw = storage.getItem(KEY)
    if (!raw) return null
    const loc = JSON.parse(raw)
    return isValidLocation(loc) ? loc : null
  } catch (e) {
    return null
  }
}

export function saveLocation(loc, storage = globalThis.localStorage) {
  if (!isValidLocation(loc)) return false
  const safe = {
    label: loc.label,
    name: loc.name || loc.label,
    admin1: loc.admin1 || null,
    admin2: loc.admin2 || null,
    country: loc.country || null,
    latitude: roundCoord(loc.latitude),
    longitude: roundCoord(loc.longitude),
    source: loc.source === 'gps' ? 'gps' : 'search',
  }
  try { storage.setItem(KEY, JSON.stringify(safe)); return true } catch (e) { return false }
}

export function clearLocation(storage = globalThis.localStorage) {
  try { storage.removeItem(KEY) } catch (e) { /* ignore */ }
}

export function loadCropChoice(storage = globalThis.localStorage) {
  try {
    const c = JSON.parse(storage.getItem(CROP_KEY) || 'null')
    return c && typeof c === 'object' ? { crop: String(c.crop || ''), stage: String(c.stage || '') } : { crop: '', stage: '' }
  } catch (e) {
    return { crop: '', stage: '' }
  }
}

export function saveCropChoice(choice, storage = globalThis.localStorage) {
  try { storage.setItem(CROP_KEY, JSON.stringify({ crop: choice.crop || '', stage: choice.stage || '' })) } catch (e) { /* ignore */ }
}
