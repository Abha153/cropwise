// Run with: npm test   (Node's built-in runner; no extra dependencies)
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  requestBrowserPosition, stateForPositionError, GEO_STATES, getGeolocationPermission,
} from '../src/utils/geolocation.js'
import {
  loadLocation, saveLocation, clearLocation, isValidLocation, loadCropChoice, saveCropChoice,
} from '../src/utils/weatherLocationStore.js'
import {
  formatHour, formatClock, formatDayShort, formatDayLong, formatUpdatedAt, ageParts, compassDirection, locationLines,
} from '../src/utils/weatherFormat.js'

const navWith = (impl) => ({ geolocation: { getCurrentPosition: impl } })
const memStorage = () => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k) } }

test('geolocation: success returns coordinates', async () => {
  const nav = navWith((ok) => ok({ coords: { latitude: 21.25, longitude: 81.63, accuracy: 30 } }))
  const r = await requestBrowserPosition({ nav, secureContext: true })
  assert.deepEqual(r, { latitude: 21.25, longitude: 81.63, accuracyMeters: 30 })
})

test('geolocation: denied, timeout, unavailable map to distinct states', async () => {
  for (const [code, state] of [[1, GEO_STATES.PERMISSION_DENIED], [3, GEO_STATES.TIMEOUT], [2, GEO_STATES.UNAVAILABLE]]) {
    const nav = navWith((_, bad) => bad({ code, message: 'x' }))
    await assert.rejects(requestBrowserPosition({ nav, secureContext: true }), (e) => e.state === state)
    assert.equal(stateForPositionError({ code }), state)
  }
})

test('geolocation: unsupported, insecure context and junk coordinates are rejected', async () => {
  await assert.rejects(requestBrowserPosition({ nav: {}, secureContext: true }), (e) => e.state === GEO_STATES.UNSUPPORTED)
  const nav = navWith(() => assert.fail('must not prompt on insecure context'))
  await assert.rejects(requestBrowserPosition({ nav, secureContext: false }), (e) => e.state === GEO_STATES.INSECURE_CONTEXT)
  const bad = navWith((ok) => ok({ coords: { latitude: 123, longitude: 10 } }))
  await assert.rejects(requestBrowserPosition({ nav: bad, secureContext: true }), (e) => e.state === GEO_STATES.UNAVAILABLE)
})

test('geolocation: permission query degrades to null', async () => {
  assert.equal(await getGeolocationPermission({}), null)
  assert.equal(await getGeolocationPermission({ permissions: { query: async () => ({ state: 'denied' }) } }), 'denied')
})

test('location store: rounds coordinates, rejects invalid, survives corrupt data', () => {
  const s = memStorage()
  assert.equal(saveLocation({ label: 'Raipur, CG', latitude: 21.251384, longitude: 81.629641, source: 'gps' }, s), true)
  const loc = loadLocation(s)
  assert.equal(loc.latitude, 21.25); assert.equal(loc.longitude, 81.63); assert.equal(loc.source, 'gps')
  assert.equal(saveLocation({ label: 'x', latitude: 95, longitude: 0 }, s), false)
  assert.equal(isValidLocation({ label: '', latitude: 1, longitude: 1 }), false)
  s.setItem('cropwise.weatherLocation.v1', '{not json')
  assert.equal(loadLocation(s), null)
  clearLocation(s); assert.equal(loadLocation(s), null)
})

test('crop choice round-trips and defaults safely', () => {
  const s = memStorage()
  assert.deepEqual(loadCropChoice(s), { crop: '', stage: '' })
  saveCropChoice({ crop: 'wheat', stage: 'flowering' }, s)
  assert.deepEqual(loadCropChoice(s), { crop: 'wheat', stage: 'flowering' })
})

test('format: location-local times are not shifted by the viewer timezone', () => {
  assert.equal(formatHour('2026-10-19T00:00'), '12 AM')
  assert.equal(formatHour('2026-10-19T13:00'), '1 PM')
  assert.equal(formatClock('2026-10-19T05:07'), '05:07')
  assert.equal(formatDayShort('2026-10-19'), 'Mon')
  // 07:45 UTC at IST (+19800 s) is 13:15 local.
  assert.match(formatUpdatedAt('2026-10-19T07:45:00Z', 19800), /19.*Oct.*13:15|Oct.*19.*13:15/)
  assert.equal(formatUpdatedAt('garbage', 0), null)
})

test('format: calendar labels and clocks follow every supported locale without timezone shifting', () => {
  const locales = ['en', 'hi', 'mr', 'bn', 'ta', 'te', 'gu', 'kn', 'ml', 'pa', 'or', 'as', 'ur', 'bho', 'mai']
  for (const locale of locales) {
    assert.ok(formatDayShort('2026-10-19', locale).length > 0, locale)
    assert.ok(formatDayLong('2026-10-19', locale).length > 0, locale)
    assert.ok(formatHour('2026-10-19T13:00', locale).length > 0, locale)
    assert.ok(formatClock('2026-10-19T05:07', locale).length > 0, locale)
    assert.ok(formatUpdatedAt('2026-10-19T07:45:00Z', 19800, locale).length > 0, locale)
  }
  assert.notEqual(formatDayShort('2026-10-19', 'en'), formatDayShort('2026-10-19', 'hi'))
  assert.notEqual(formatDayLong('2026-10-19', 'en'), formatDayLong('2026-10-19', 'hi'))
})

test('format: age, compass and location lines', () => {
  assert.deepEqual(ageParts(30), { unit: 'seconds', value: 30 })
  assert.deepEqual(ageParts(600), { unit: 'minutes', value: 10 })
  assert.deepEqual(ageParts(7200), { unit: 'hours', value: 2 })
  assert.equal(ageParts(-1), null)
  assert.equal(compassDirection(0), 'N'); assert.equal(compassDirection(359), 'N'); assert.equal(compassDirection(90), 'E')
  assert.deepEqual(locationLines({ name: 'Bilaspur', admin2: 'Bilaspur', admin1: 'Chhattisgarh', country: 'India' }),
    { title: 'Bilaspur', subtitle: 'Chhattisgarh, India' })
})

import { weatherConditionKey, iconForWeatherCode } from '../src/utils/weatherCodes.js'

test('weather conditions: every supported WMO code has a localized translation key', () => {
  const cases = [
    [0, 'clear'], [1, 'mainlyClear'], [2, 'partlyCloudy'], [3, 'overcast'],
    [45, 'fog'], [48, 'fog'], [51, 'drizzle'], [55, 'drizzle'],
    [56, 'freezingDrizzle'], [57, 'freezingDrizzle'], [61, 'rain'], [65, 'rain'],
    [66, 'freezingRain'], [67, 'freezingRain'], [71, 'snow'], [77, 'snow'],
    [80, 'showers'], [82, 'showers'], [85, 'snowShowers'], [86, 'snowShowers'],
    [95, 'thunderstorm'], [96, 'thunderstorm'], [99, 'thunderstorm'], [999, 'unknown'],
  ]
  for (const [code, suffix] of cases) {
    assert.equal(weatherConditionKey(code), `weatherPage.condition.${suffix}`)
    assert.ok(iconForWeatherCode(code))
  }
})


test('weather localization: all 15 locales include every weather key and preserve interpolation placeholders', async () => {
  const locales = ['en', 'hi', 'mr', 'bn', 'ta', 'te', 'gu', 'kn', 'ml', 'pa', 'or', 'as', 'ur', 'bho', 'mai']
  const dictionaries = Object.fromEntries(locales.map((locale) => [
    locale,
    JSON.parse(readFileSync(new URL(`../src/i18n/translations/${locale}.json`, import.meta.url), 'utf8')),
  ]))
  const reference = dictionaries.en
  const weatherKeys = Object.keys(reference).filter((key) => key.startsWith('weatherPage.'))
  const placeholders = (value) => [...String(value).matchAll(/{{\s*([^}\s]+)\s*}}/g)].map((match) => match[1]).sort()
  assert.ok(weatherKeys.length > 0, 'English weather translation keys should exist')
  for (const locale of locales) {
    for (const key of weatherKeys) {
      assert.ok(Object.hasOwn(dictionaries[locale], key), `${locale} is missing ${key}`)
      assert.deepEqual(placeholders(dictionaries[locale][key]), placeholders(reference[key]), `${locale} has different placeholders for ${key}`)
      assert.equal(typeof dictionaries[locale][key], 'string', `${locale} value for ${key} must be text`)
      assert.ok(dictionaries[locale][key].trim().length > 0, `${locale} value for ${key} must not be empty`)
    }
  }
})
