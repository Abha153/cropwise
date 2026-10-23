import React, { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Crosshair, Search, MapPin, Loader2, X, AlertCircle } from 'lucide-react'
import { api } from '../../api/client'
import { useI18n } from '../../i18n/I18nContext'
import {
  requestBrowserPosition, getGeolocationPermission, GEO_STATES,
} from '../../utils/geolocation'
import { locationLines } from '../../utils/weatherFormat'
import { roundCoord } from '../../utils/weatherLocationStore'

const DEBOUNCE_MS = 350
const MIN_QUERY = 2

const GEO_MESSAGE_KEY = {
  [GEO_STATES.PERMISSION_DENIED]: 'weatherPage.loc.permissionDenied',
  [GEO_STATES.TIMEOUT]: 'weatherPage.loc.timeout',
  [GEO_STATES.UNAVAILABLE]: 'weatherPage.loc.unavailable',
  [GEO_STATES.UNSUPPORTED]: 'weatherPage.loc.unsupported',
  [GEO_STATES.INSECURE_CONTEXT]: 'weatherPage.loc.insecure',
}

/**
 * Location chooser for the weather page.
 *
 *  - "Use My Location": asks the browser for ONE position when clicked (never
 *    automatically, never repeatedly), names it via reverse geocoding, and
 *    reports it with source:'gps'. If the browser already reports the
 *    permission as denied it does not call the API again; it explains how to
 *    re-enable it. Manual search always keeps working.
 *  - Search: debounced autocomplete over the backend geocoder (place names,
 *    villages, districts, states, PIN codes, or "lat, lon").
 *
 * Props: selected (location | null), onSelect(location), onClear().
 */
export default function LocationPicker({ selected, onSelect, onClear }) {
  const { t, code } = useI18n()
  const uid = useId()
  const listId = `${uid}-list`
  const inputRef = useRef(null)
  const rootRef = useRef(null)
  const searchAbort = useRef(null)

  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState({ status: 'idle', results: [] }) // idle|loading|done|error
  const [active, setActive] = useState(-1)
  const [geo, setGeo] = useState({ status: 'idle', messageKey: null }) // idle|detecting|error

  // ---- debounced search --------------------------------------------------
  useEffect(() => {
    const q = query.trim()
    if (searchAbort.current) searchAbort.current.abort()
    if (q.length < MIN_QUERY) { setSearch({ status: 'idle', results: [] }); return undefined }
    const controller = new AbortController()
    searchAbort.current = controller
    setSearch((s) => ({ status: 'loading', results: s.results }))
    const timer = setTimeout(() => {
      api.searchLocations(q, { signal: controller.signal, language: ['bho', 'mai'].includes(code) ? 'hi' : code })
        .then((res) => { setSearch({ status: 'done', results: res.results || [] }); setActive(-1) })
        .catch((err) => { if (err && err.name === 'AbortError') return; setSearch({ status: 'error', results: [], message: err && err.message }) })
    }, DEBOUNCE_MS)
    return () => { clearTimeout(timer); controller.abort() }
  }, [query, code])

  useEffect(() => {
    const onDocClick = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  const choose = useCallback((r) => {
    onSelect({
      label: r.label, name: r.name, admin1: r.admin1, admin2: r.admin2, country: r.country,
      latitude: r.latitude, longitude: r.longitude, source: 'search',
    })
    setQuery(''); setOpen(false); setActive(-1); setGeo({ status: 'idle', messageKey: null })
  }, [onSelect])

  function onKeyDown(e) {
    const rows = search.results
    if (e.key === 'ArrowDown') {
      e.preventDefault(); setOpen(true)
      if (rows.length) setActive((a) => (a + 1) % rows.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (rows.length) setActive((a) => (a <= 0 ? rows.length - 1 : a - 1))
    } else if (e.key === 'Enter') {
      if (open && active >= 0 && rows[active]) { e.preventDefault(); choose(rows[active]) }
      else if (open && rows.length === 1) { e.preventDefault(); choose(rows[0]) }
    } else if (e.key === 'Escape') {
      setOpen(false); setActive(-1)
    }
  }

  // ---- Use My Location ---------------------------------------------------
  async function useMyLocation() {
    if (geo.status === 'detecting') return
    setGeo({ status: 'detecting', messageKey: null })
    // Don't call the API again when the browser already says "denied": the
    // call would fail instantly anyway, and the user needs instructions.
    if ((await getGeolocationPermission()) === 'denied') {
      setGeo({ status: 'error', messageKey: GEO_MESSAGE_KEY[GEO_STATES.PERMISSION_DENIED] })
      return
    }
    let pos
    try {
      pos = await requestBrowserPosition()
    } catch (err) {
      setGeo({ status: 'error', messageKey: GEO_MESSAGE_KEY[err.state] || GEO_MESSAGE_KEY[GEO_STATES.UNAVAILABLE] })
      return
    }
    let place = null
    try {
      place = await api.reverseGeocode(pos.latitude, pos.longitude, { language: ['bho', 'mai'].includes(code) ? 'hi' : code })
    } catch (e) { /* fall through: show coordinates, never an invented name */ }
    const lat = roundCoord(pos.latitude), lon = roundCoord(pos.longitude)
    const coordsLabel = t('weatherPage.loc.coordsLabel', { lat: lat.toFixed(2), lon: lon.toFixed(2) })
    onSelect({
      label: place ? place.label : coordsLabel,
      name: place ? place.name : coordsLabel,
      admin1: place ? place.admin1 : null, admin2: place ? place.admin2 : null,
      country: place ? place.country : null,
      latitude: lat, longitude: lon, source: 'gps', nameFound: !!place,
    })
    setGeo({ status: 'idle', messageKey: null })
  }

  const showList = open && query.trim().length >= MIN_QUERY
  const { title, subtitle } = locationLines(selected)

  return (
    <div ref={rootRef} className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink/50 dark:text-paper/50">
            {t('weatherPage.loc.selected')}
          </div>
          {selected ? (
            <div className="flex items-start gap-1.5 mt-0.5">
              <MapPin size={16} className="text-forest dark:text-forest-light mt-1 shrink-0" aria-hidden="true" />
              <div className="min-w-0">
                <div className="font-display text-lg font-semibold leading-tight break-words">{title}</div>
                {subtitle && <div className="text-xs text-ink/60 dark:text-paper/60 break-words">{subtitle}</div>}
                {selected.source === 'gps' && (
                  <div className="text-[11px] text-ink/50 dark:text-paper/50 mt-0.5">
                    {t('weatherPage.loc.fromDevice')}
                    {selected.nameFound === false && ` · ${t('weatherPage.loc.nameUnknown')}`}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-sm text-ink/60 dark:text-paper/60 mt-0.5">{t('weatherPage.loc.none')}</div>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            type="button" onClick={useMyLocation} disabled={geo.status === 'detecting'}
            className="inline-flex items-center justify-center gap-2 bg-forest text-paper font-semibold rounded-lg px-4 py-2.5 text-sm hover:bg-forest-dark transition-colors disabled:opacity-70 min-h-[44px] flex-1 sm:flex-none focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold"
          >
            {geo.status === 'detecting'
              ? <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              : <Crosshair size={16} aria-hidden="true" />}
            {geo.status === 'detecting' ? t('weatherPage.loc.detecting') : t('weatherPage.loc.useMyLocation')}
          </button>
          {selected && (
            <button
              type="button" onClick={() => { onClear(); setGeo({ status: 'idle', messageKey: null }); inputRef.current && inputRef.current.focus() }}
              className="inline-flex items-center gap-1 border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm text-ink/70 dark:text-paper/70 hover:bg-mist dark:hover:bg-white/10 min-h-[44px] focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold"
              aria-label={t('weatherPage.loc.clearAria')}
            >
              <X size={14} aria-hidden="true" /> {t('weatherPage.loc.clear')}
            </button>
          )}
        </div>
      </div>

      {geo.status === 'error' && geo.messageKey && (
        <div role="alert" className="flex items-start gap-2 text-sm bg-marigold/15 text-ink dark:text-paper rounded-lg px-3 py-2 mb-3">
          <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{t(geo.messageKey)}</span>
        </div>
      )}
      <div role="status" aria-live="polite" className="sr-only">
        {geo.status === 'detecting' ? t('weatherPage.loc.detecting') : ''}
      </div>

      <label htmlFor={`${uid}-input`} className="block text-xs font-medium text-ink/60 dark:text-paper/60 mb-1">
        {selected ? t('weatherPage.loc.changeLabel') : t('weatherPage.loc.searchLabel')}
      </label>
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/40 dark:text-paper/40 pointer-events-none" aria-hidden="true" />
        <input
          ref={inputRef} id={`${uid}-input`} type="text" value={query} autoComplete="off" spellCheck={false}
          role="combobox" aria-expanded={showList} aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${uid}-opt-${active}` : undefined}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)} onKeyDown={onKeyDown}
          placeholder={t('weatherPage.loc.searchPlaceholder')}
          className="w-full border border-black/10 dark:border-white/15 rounded-lg pl-9 pr-9 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper min-h-[44px] focus:outline-none focus:ring-2 focus:ring-forest/40"
        />
        {search.status === 'loading' && (
          <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-ink/40 dark:text-paper/40" aria-hidden="true" />
        )}
        {showList && (
          <ul
            id={listId} role="listbox" aria-label={t('weatherPage.loc.resultsAria')}
            className="absolute z-20 left-0 right-0 mt-1 max-h-72 overflow-auto bg-white dark:bg-charcoal border border-black/10 dark:border-white/15 rounded-xl shadow-lifted"
          >
            {search.status === 'loading' && search.results.length === 0 && (
              <li role="presentation" className="px-3 py-3 text-sm text-ink/60 dark:text-paper/60">{t('weatherPage.loc.searching')}</li>
            )}
            {search.status === 'error' && (
              <li role="presentation" className="px-3 py-3 text-sm">
                <span className="text-clay">{t('weatherPage.loc.searchError')}</span>{' '}
                <button type="button" className="underline text-forest dark:text-forest-light" onClick={() => setQuery((q) => q + ' ')}>
                  {t('weatherPage.retry')}
                </button>
              </li>
            )}
            {search.status === 'done' && search.results.length === 0 && (
              <li role="presentation" className="px-3 py-3 text-sm text-ink/60 dark:text-paper/60">{t('weatherPage.loc.noResults')}</li>
            )}
            {search.results.map((r, i) => {
              const sub = [r.admin2, r.admin1, r.country].filter((p, j, a) => p && p !== r.name && a.indexOf(p) === j).join(', ')
              return (
                <li
                  key={r.id} id={`${uid}-opt-${i}`} role="option" aria-selected={i === active}
                  onMouseDown={(e) => { e.preventDefault(); choose(r) }}
                  onMouseEnter={() => setActive(i)}
                  className={`px-3 py-2.5 cursor-pointer text-sm border-b last:border-b-0 border-black/5 dark:border-white/10 ${i === active ? 'bg-forest/10 dark:bg-white/10' : ''}`}
                >
                  <div className="font-medium">{r.name}</div>
                  <div className="text-xs text-ink/60 dark:text-paper/60">
                    {r.kind === 'coordinates' ? t('weatherPage.loc.coordsResult') : sub}
                    {r.postcodes && r.postcodes.length > 0 && ` · ${r.postcodes[0]}`}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
      <p className="text-[11px] text-ink/50 dark:text-paper/50 mt-2">{t('weatherPage.loc.privacyNote')}</p>
    </div>
  )
}
