# CropWise MVP Audit

Produced by direct inspection of `CropWise_RegressionFix_CHECKPOINT.zip`. Every
finding below cites the actual file(s) inspected. Areas not inspected in
depth are marked "NOT AUDITED" rather than guessed at (per the no-fabrication
rule this audit is itself subject to).

Legend: **COMPLETE** / **PARTIAL** / **MISSING** / **BROKEN**

---

## Ask Assistant / NLU / Intent detection — **BROKEN**

Files: `backend/app/routers/assistant.py`, `backend/app/i18n/{intents,nlu,templates}.py`

What's real and working:
- A genuine language-neutral pipeline exists: `nlu.parse()` → intent +
  entities → intent-specific handler → templated native-language response.
  This is the right shape and is not a stub.
- Entity extraction (`crop`, `quantity_kg`, `location`) is real, with
  quintal→kg conversion and multi-language unit words.
- Conversation context carry-forward (`known_crop`/`known_quantity_kg`/
  `known_location`) is implemented and wired through the router.
- `DISEASE_HELP` and `GENERAL_AGRICULTURE_QUERY` correctly return an honest
  "CropWise doesn't have that data" response rather than a guess.

Confirmed problems (exactly the ones the spec anticipated, not assumed):
1. **`detect_intent()` still defaults unmatched input to
   `MARKET_RECOMMENDATION` unconditionally** (`intents.py` line 145,
   comment literally says "the overwhelmingly common case for this
   assistant"). There is no confidence concept and no
   `clarification_needed` path for genuinely ambiguous questions — only for
   missing crop/location once an intent is already assumed. This is
   exactly the "never default randomly to market recommendation" bug
   called out in the spec.
2. **`PRICE_LOOKUP` is a dead intent.** It's declared as a constant
   (`intents.py` line 4) but has zero keywords in `INTENT_KEYWORDS` and is
   never referenced in `assistant.py` or `templates.py` — it can never be
   produced or handled.
3. **`PRICE_FORECAST`, `PROFIT_CALCULATION`, `FARMPOOL`, and
   `BUYER_SEARCH` are not routed to their own business logic.** In
   `assistant.py` (lines 131–141) all four fall through to the same
   `compare_markets(...)` call used for `MARKET_RECOMMENDATION` — the code
   comment admits this directly. `price_predictor.predict_next_days`
   (used correctly by `routers/forecast.py`) is never imported into
   `assistant.py`; neither is `profit.py`'s logic, `FarmPool` logic, or
   `services/buyer_matcher.py` (only used by `routers/matching.py`). So
   asking the assistant "what's tomorrow's price" or "find me a buyer"
   currently returns a market-comparison answer, not a forecast or buyer
   list.
4. `_extract_quantity_kg` recognizes "kg" and "quintal" (and their
   translations) but not "ton"/"tonne" — the spec's own example ("I have 1
   tonne onion near Nashik") would not parse a quantity today.
5. No assistant/NLU test file exists (`backend/tests/` has weather, mandi
   directory, market router, and login-tracking tests only — nothing
   exercises `nlu.parse()`, `detect_intent()`, or `/assistant/ask`).

## Multilingual system — **PARTIAL, gap is as large as the spec describes**

Files: `frontend/src/i18n/*`, all of `frontend/src/pages/*.jsx` and
`frontend/src/components/*.jsx`

- Backend NLU-side language support is comparatively strong: 15 language
  translation JSON files exist, plus a genuine keyword-based multi-language
  intent/entity system (`backend/app/i18n/*.py`, ~670 lines).
- Frontend UI-string translation is the real gap. `en.json` (and every
  other locale file, all the same length) has **30 keys total** — nav
  labels, the landing hero, and a few Ask Assistant strings. Nothing else.
- Grepping `t(`/`useI18n`/`useTranslation` usage per file confirms this
  quantitatively: `SellingJourney.jsx`, `StatCard.jsx`, `Badge.jsx`,
  `LoadingSpinner.jsx` have **zero** calls despite `SellingJourney.jsx`
  alone containing 15+ hardcoded English strings ("Your Selling Journey",
  "Add Produce →", "Journey complete", stage labels, etc.). Most page
  files have single digits of `t()` calls against pages that visibly have
  dozens of labels, buttons, and empty/error states (Farmer Dashboard,
  Market Intelligence, AI Advisor, Notifications, BuyerDashboard, etc. all
  fall in this bucket).
- A handful of pages (`AskAssistant.jsx` 27, `BuyerDemands.jsx` 28,
  `Lots.jsx` 26, `LotsManager.jsx` 19, `TransactionDetail.jsx` 18) are
  meaningfully translated.
- RTL (Urdu) support: `languages.js`/`I18nContext.jsx` were not read in
  full this pass — **NOT AUDITED** whether `dir="rtl"` is actually applied
  and whether any layout breaks under it.

## GPS / Location — **PARTIAL**

Files: `frontend/src/utils/location.js`, `WeatherCard.jsx`,
`MarketIntelligence.jsx`

- Real infrastructure exists: `requestGeolocatedMarket()` calls
  `navigator.geolocation.getCurrentPosition`, resolves to a real backend
  nearest-market lookup, and never fabricates coordinates or distance.
  `resolveDefaultLocation()` correctly prefers saved profile location over
  a demo default, and the demo default is explicitly documented as a
  fallback, not a restriction.
- Gap: the promise simply `reject(err)`s on any geolocation failure
  (permission denied, timeout, position unavailable, unsupported) with no
  differentiation — there's no explicit state machine matching the spec's
  IDLE / DETECTING / SUCCESS / PERMISSION_DENIED / TIMEOUT / UNAVAILABLE /
  UNSUPPORTED states. Callers would have to inspect the raw
  `GeolocationPositionError.code` themselves; **not confirmed** either
  `WeatherCard.jsx` or `MarketIntelligence.jsx` currently do this
  (NOT AUDITED at the line level yet).
- Only two call sites (`WeatherCard.jsx`, `MarketIntelligence.jsx`) use
  geolocation at all — Farmer Dashboard's own location context was not
  traced this pass (NOT AUDITED whether it independently manages a
  location value that GPS could conflict with).
- "manual selection survives a failed GPS attempt" — plausible given the
  promise-rejection design (nothing overwrites state on rejection by
  construction) but **not confirmed by reading each caller's error
  handler**.

## Weather — **near COMPLETE, matches the spec's own description well**

Files: `backend/app/services/weather_service.py` (414 lines),
`WeatherCard.jsx`

- LIVE (Open-Meteo) / DEMO (deterministic seeded) / UNAVAILABLE states are
  real and implemented as described: `get_weather()` tries live fetch
  first, falls back to a hand-authored per-location 7-day seeded table
  only on live failure, and returns UNAVAILABLE (not fake data) if neither
  resolves.
- The DEMO dataset uses an explicit fixed anchor date (`dt.date(2026, 9,
  2)`, `weather_service.py` line 185) specifically so it can't be mistaken
  for "today's real weather" — this directly satisfies the spec's date
  concern.
- Source is surfaced explicitly (`"source": "Open-Meteo"` vs `"CropWise
  Demo Dataset"` vs `None`), with rain/clear-sky code consistency
  documented as a deliberate authoring rule.
- Frontend rendering of these three states in `WeatherCard.jsx`, AI
  Advisor's use of weather, and mobile presentation — **NOT AUDITED** at
  the line level this pass (file was listed but not opened).

## Selling Journey — **mostly COMPLETE structurally, translation is the gap**

File: `frontend/src/components/SellingJourney.jsx` (167 lines)

- Five stages, Lucide icons only (`Sprout`, `BarChart3`, `Handshake`,
  `Truck`, `CircleCheck` — the file's own comment confirms this replaced a
  previous emoji set), no gamification (no XP/points/badges anywhere in
  the file).
- Stage status (`completed`/`current`/`upcoming`), current-stage panel,
  next-action CTA, and the fully-complete state are all driven from a
  `journey` prop (`stageStatus`, `currentStageKey`, `lot`, `transaction`,
  `isFullyComplete`) rather than hardcoded — **but** `utils/sellingJourney.js`,
  which presumably derives that object from real app state, was not opened
  this pass to confirm progress is never hardcoded (NOT AUDITED).
- Desktop (horizontal) and mobile (vertical timeline) layouts both exist
  in this one component.
- Every string in this component is hardcoded English with zero `t()`
  calls — this is the multilingual gap's single most visible instance
  since it's a "signature UX" component per the spec.

## Buyer discovery / Marketplace / Transactions / Payments / Group
Selling / FarmPool / Storage / Quality / AI Advisor — **NOT AUDITED**

These have real backend routers/services (`buyer_matcher.py`,
`recommendation_engine.py`, `transport_optimizer.py`,
`quality_grading.py`, dedicated routers for each) and corresponding
frontend pages, but I have not opened them this pass. I'm not reporting a
status for them rather than guessing — they need the same file-level read
the areas above got before any claim (COMPLETE/PARTIAL/MISSING/BROKEN) is
credible.

## Price forecasting — **COMPLETE as a deterministic baseline, correctly not ML**

File: `backend/app/services/price_predictor.py` (113 lines)

- Genuine least-squares trend + volatility-band model, no ML dependency.
- `backtest_accuracy()` is a real walk-forward backtest (predicts t+1 from
  data[0:t] only, compares to the actual recorded price) — MAE/RMSE/MAPE
  are computed from real prediction-vs-actual pairs, not invented; returns
  `None` outright when there isn't enough history rather than fabricating
  a number.
- `confidence_pct` is a real formula (`90 - volatility*380`, clamped
  35–93) — it's a heuristic, not a calibrated statistical confidence
  interval, and should probably be labeled as such in the UI, but it is
  not fabricated/random.
- `PriceForecast.jsx` already asks "Uses machine learning?" and answers
  "No" from `result.methodology.is_machine_learning` — this is honest, not
  a mislabel. I did not find any frontend or backend string claiming this
  is ML/AI-trained.
- Internal docstring comments mention Prophet/XGBoost/LSTM as a *future*
  integration point for developers — this is developer documentation, not
  user-facing wording, so it doesn't violate the "don't call it ML"
  requirement, but could be trimmed for cleanliness.

## Avatars / Branding (from the prior checkpoint) — **COMPLETE**

Confirmed still present and correctly separated in this checkpoint:
`frontend/public/avatars/{farmers,buyers}/*.png` (10 files),
`frontend/src/utils/avatars.js`, `frontend/src/components/Avatar.jsx`, and
the CropWise favicon set remain distinct from user avatars.

## Meta / OG / positioning — **COMPLETE**

`frontend/index.html` already uses the exact spec-requested title/OG text:
"CropWise — Smart Agricultural Market Intelligence for Farmers & Buyers",
with a matching description mentioning mandi prices, buyer matching,
transport, storage, and transparent transactions. Not verified whether
"verified buyers" language is backed by real data everywhere it appears
(`buyer_verification.py` router exists, suggesting it's genuine, but this
wasn't traced end-to-end).

## Test coverage — **PARTIAL, notable gap on the assistant**

`backend/tests/` contains 5 files (706 lines): weather service, weather
router integration, mandi directory, market router, login tracking. There
is **no test file exercising `/assistant/ask`, `nlu.parse()`, or
`detect_intent()`** — none of the scenario questions in the spec's testing
section (§24) currently have automated coverage. Frontend has no test
files at all in what was inspected (not exhaustively confirmed).

---

## Honest summary of this audit's own limits

I read and can back with file/line citations: `assistant.py`, `intents.py`,
`nlu.py`, `price_predictor.py`, `weather_service.py` (partially — the LIVE
fetch and frontend rendering code was not read), `location.js`,
`SellingJourney.jsx`, `index.html`, the i18n translation JSON files (key
counts only), and did a repo-wide grep for `t(` usage and ML-related
wording.

I did **not** read: Marketplace/Lots/Transactions/Payments/BuyerVerification/
GroupSelling/FarmPool/Storage/Quality pages or their backend routers/services,
`utils/sellingJourney.js`, `WeatherCard.jsx`'s actual rendering logic,
`I18nContext.jsx`/RTL handling, or any frontend test files. No browser/UI
testing was performed (no responsive breakpoints, no live Open-Meteo HTTP
call was exercised, no language was manually clicked through). Anything
above framed as COMPLETE reflects the code I actually read, not the whole
system.

## Recommended next step

Given the size of what's left (§3–§10 of the brief alone touch the
assistant router, 3+ backend service integrations, and translation of
~10 major page surfaces), I'd suggest tackling this in checkpointed
batches rather than one pass:

1. **Assistant routing fix** (§3–§8): wire `PRICE_FORECAST` →
   `price_predictor`, `PROFIT_CALCULATION` → `profit` logic,
   `BUYER_SEARCH` → `buyer_matcher`, add `PRICE_LOOKUP` keywords +
   handler, replace the unconditional `MARKET_RECOMMENDATION` default with
   a real `clarification_needed` low-confidence path, add "ton/tonne"
   parsing, add assistant test coverage. This is self-contained and
   testable in isolation.
2. **Multilingual pass** (§9–§10): expand `en.json`+all 15 locale files
   and wire `t()` calls through the highest-traffic surfaces first
   (Farmer Dashboard, Selling Journey, Market Intelligence, Marketplace),
   then the rest.
3. **GPS state machine + remaining area audits** (§11–§12, plus actually
   reading Marketplace/Transactions/Payments/etc. before touching them).
4. **Selling Journey / positioning polish** (§16–§20) — smallest remaining
   gap given what's already correct.

Each batch would end with an actual test run and a fresh checkpoint zip,
per the standing backup rule.
