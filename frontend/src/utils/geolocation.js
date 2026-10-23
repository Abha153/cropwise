// Browser geolocation, used by the weather page's "Use My Location" button.
//
// Deliberately small and strict:
//   * ONE getCurrentPosition call per explicit user click -- never
//     watchPosition, never polling, never a background request.
//   * Every outcome maps to a distinct `state` so the UI can say why it
//     failed (denied / timeout / unavailable / unsupported / insecure).
//   * No silent fallback to an IP-based or default location: on failure the
//     caller keeps whatever the user had selected and offers manual search.
//
// (utils/location.js has a separate helper that resolves GPS to the nearest
// MARKET; this one only returns coordinates.)

export const GEO_STATES = {
  PERMISSION_DENIED: 'PERMISSION_DENIED',
  TIMEOUT: 'TIMEOUT',
  UNAVAILABLE: 'UNAVAILABLE',
  UNSUPPORTED: 'UNSUPPORTED',
  INSECURE_CONTEXT: 'INSECURE_CONTEXT',
}

export const GEO_TIMEOUT_MS = 10000
export const GEO_MAX_AGE_MS = 5 * 60 * 1000

function geoError(state, message) {
  return Object.assign(new Error(message), { state })
}

export function isGeolocationSupported(nav = globalThis.navigator) {
  return !!(nav && nav.geolocation && typeof nav.geolocation.getCurrentPosition === 'function')
}

// Maps a GeolocationPositionError code (MDN: 1 denied, 2 unavailable,
// 3 timeout) to our state names.
export function stateForPositionError(err) {
  if (err && err.code === 1) return GEO_STATES.PERMISSION_DENIED
  if (err && err.code === 3) return GEO_STATES.TIMEOUT
  return GEO_STATES.UNAVAILABLE
}

/**
 * Resolves { latitude, longitude, accuracyMeters } or rejects with an Error
 * whose `.state` is one of GEO_STATES.
 */
export function requestBrowserPosition({
  nav = globalThis.navigator,
  secureContext = globalThis.isSecureContext,
  timeoutMs = GEO_TIMEOUT_MS,
} = {}) {
  return new Promise((resolve, reject) => {
    if (!isGeolocationSupported(nav)) {
      reject(geoError(GEO_STATES.UNSUPPORTED, 'Geolocation is not supported by this browser.'))
      return
    }
    // Browsers only expose geolocation on HTTPS (or localhost). Say so
    // instead of surfacing a confusing generic failure.
    if (secureContext === false) {
      reject(geoError(GEO_STATES.INSECURE_CONTEXT, 'Geolocation requires a secure (HTTPS) connection.'))
      return
    }
    nav.geolocation.getCurrentPosition(
      (pos) => {
        const c = pos && pos.coords
        if (!c || !Number.isFinite(c.latitude) || !Number.isFinite(c.longitude)
            || Math.abs(c.latitude) > 90 || Math.abs(c.longitude) > 180) {
          reject(geoError(GEO_STATES.UNAVAILABLE, 'The device returned unusable coordinates.'))
          return
        }
        resolve({ latitude: c.latitude, longitude: c.longitude, accuracyMeters: c.accuracy ?? null })
      },
      (err) => reject(geoError(stateForPositionError(err), (err && err.message) || 'Location unavailable.')),
      { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: GEO_MAX_AGE_MS },
    )
  })
}

// Best-effort read of the browser's permission state ('granted' | 'denied' |
// 'prompt' | null when the Permissions API is unavailable). Lets the UI avoid
// re-prompting after a denial and explain how to re-enable instead.
export async function getGeolocationPermission(nav = globalThis.navigator) {
  try {
    if (nav && nav.permissions && nav.permissions.query) {
      const status = await nav.permissions.query({ name: 'geolocation' })
      return status.state
    }
  } catch (e) { /* unsupported -- fall through */ }
  return null
}
