# Weather & Location

A location-aware weather page (`/weather`) with farming advisories.

## How it works
- **Location**: "Use My Location" (one browser prompt per click, no tracking) or search by
  city / village / district / state / PIN / "lat, lon". Only an explicitly chosen place is remembered
  (localStorage, coordinates rounded to ~1 km). A denied permission never blocks manual search.
- **Backend** (`backend/app/`): `routers/weather.py` (HTTP), `services/open_meteo_provider.py`
  (provider adapter + normalisation), `services/geocoding_service.py` (Open-Meteo geocoding,
  Nominatim reverse), `services/weather_service.py` (cache, request dedup, stale handling,
  seeded DEMO fallback), `services/farm_advisory.py` (rule-based advisory engine).
- **Frontend**: `pages/Weather.jsx`, `components/weather/*`, `hooks/useWeatherData.js`,
  `utils/{geolocation,weatherLocationStore,weatherFormat}.js`.
- **Data honesty**: responses are labelled LIVE / STALE (with age) / DEMO / UNAVAILABLE.
  Advisories are CropWise rules, never presented as IMD alerts; ET0 is not crop water use.

## Endpoints
`GET /weather/farmer` (auth) · `GET /weather?latitude&longitude&location&include_advisory&crop&growth_stage`
· `GET /weather/geocode/search?q=` · `GET /weather/geocode/reverse?latitude&longitude`

## Configuration (backend env, all optional; see `backend/.env.example`)
`OPEN_METEO_API_KEY`, `OPEN_METEO_BASE_URL`, `OPEN_METEO_GEOCODING_URL`, `NOMINATIM_BASE_URL`,
`GEOCODER_USER_AGENT`. Open-Meteo's free tier is **non-commercial only**; set a key and customer
endpoint for commercial use. Nominatim requires an identifying User-Agent and <=1 request/second.
Set these in the Render dashboard (backend). The Vercel frontend needs no new variables.

## Tests
- Backend: `cd backend && python -m pytest`
- Frontend utilities: `cd frontend && npm test` (Node built-in runner, no new dependencies)
- Build: `cd frontend && npm run build`

## Known limitations
- The live Open-Meteo/Nominatim round trip was not verified from the development sandbox
  (outbound access blocked); verify once on a deployed backend.
- Only English strings exist for the new weather UI keys; other locales fall back to English.
- No automated browser/mobile-layout test; check `/weather` at phone width manually.
- Pre-existing, unrelated: `backend/tests/test_reputation_seed.py::test_buyer_profiles` fails on a clean checkout.
