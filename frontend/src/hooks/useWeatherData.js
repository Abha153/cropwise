import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

// Loads weather (+ advisory) for a selected location.
//
//  * Results are cached in memory for 5 minutes per (location, crop, stage),
//    so switching back to a recent place does not call the API again.
//    The server has its own cache and labels data as stale when a refresh
//    failed -- this layer only avoids redundant round trips.
//  * Identical in-flight requests are shared (request deduplication).
//  * A superseded request is aborted and its result ignored, so a slow
//    response for the previous place can never overwrite the new one.
//  * On a failed refresh the previous data for the SAME place stays on screen
//    alongside the error; data for a different place is never shown.

export const CLIENT_CACHE_TTL_MS = 5 * 60 * 1000
const cache = new Map()      // key -> { at, data }
const inflight = new Map()   // key -> Promise

export function weatherCacheKey(loc, crop, stage) {
  if (!loc) return null
  return [loc.latitude.toFixed(2), loc.longitude.toFixed(2), crop || '', stage || ''].join('|')
}

export function clearWeatherClientCache() {
  cache.clear()
  inflight.clear()
}

function fetchShared(loc, crop, stage, key, signal) {
  if (inflight.has(key)) return inflight.get(key)
  const p = api.getWeatherByLocation(loc.latitude, loc.longitude, loc.name || loc.label, {
    advisory: true, crop, growthStage: stage, signal,
  }).then((data) => {
    cache.set(key, { at: Date.now(), data })
    return data
  }).finally(() => { if (inflight.get(key) === p) inflight.delete(key) })
  inflight.set(key, p)
  // An aborted request must not stay shared: the next identical request
  // (e.g. React StrictMode's second effect run) has to start its own fetch.
  if (signal) signal.addEventListener('abort', () => { if (inflight.get(key) === p) inflight.delete(key) }, { once: true })
  return p
}

export function useWeatherData(location, { crop = '', stage = '' } = {}) {
  const [state, setState] = useState({ status: 'idle', data: null, error: null })
  const reqId = useRef(0)
  const abortRef = useRef(null)

  const load = useCallback((force) => {
    if (!location) { setState({ status: 'idle', data: null, error: null }); return }
    const key = weatherCacheKey(location, crop, stage)
    const hit = cache.get(key)
    if (!force && hit && Date.now() - hit.at < CLIENT_CACHE_TTL_MS) {
      setState({ status: 'success', data: hit.data, error: null, fromClientCache: true })
      return
    }
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const id = ++reqId.current
    setState((s) => ({ status: 'loading', data: hit ? hit.data : (s.key === key ? s.data : null), error: null, key }))
    fetchShared(location, crop, stage, key, controller.signal)
      .then((data) => { if (id === reqId.current) setState({ status: 'success', data, error: null, key }) })
      .catch((err) => {
        if (id !== reqId.current || (err && err.name === 'AbortError')) return
        setState((s) => ({ status: 'error', data: s.key === key ? s.data : null, error: err.message || 'Request failed', key }))
      })
  }, [location && location.latitude, location && location.longitude, location && (location.name || location.label), crop, stage])

  useEffect(() => {
    load(false)
    return () => { if (abortRef.current) abortRef.current.abort() }
  }, [load])

  const refresh = useCallback(() => load(true), [load])
  return { ...state, refresh }
}
