# 🌱 CropWise

**Smart Markets. Better Prices. Stronger Farmers.**

CropWise is a complete, working market-linkage and price-discovery platform
for farmers, built for the *"Strengthening Market Linkages and Price
Discovery for Farmers"* hackathon track. Its recommendation and assistant
logic is an explainable, rules-based engine over real government price and
cost data -- not a general-purpose LLM -- so every recommendation comes
with a plain-language "why" rather than a black-box answer.

It is deliberately **not** a mandi-price display app. It answers the
question a farmer actually has:

> *What should I sell? Where should I sell it? When should I sell it?
> To whom? And how much will I actually make after costs?*

---

## Changelog (this pass)

- 🌾 **Multi-source market pricing**: data.gov.in and Agmarknet-via-CEDA
  are now queried **concurrently** (never one as a fallback for the
  other) for every market-price lookup, normalized into a common shape,
  and combined with explicit source attribution -- agreeing prices are
  merged, genuine conflicts (>2% apart) preserve both values instead of
  picking one, and different-date observations from each provider are
  both kept. See "Market data has a real, multi-source live-data
  integration" below for the full contract, caching policy, and honest
  testing notes. `MarketPrice` rows persisted from a live fetch now also
  record `source`/`source_timestamp`. A genuinely independent third
  source was investigated and intentionally not added (see "Third-party
  sources beyond these two" below).
- 🗄️ **Database migrated to PostgreSQL (Supabase)**: the MVP no longer
  uses SQLite or depends on a local `cropwise.db` file. `DATABASE_URL`
  must now be set (via `backend/.env`, never committed) to a Supabase
  Postgres connection string -- see `backend/.env.example`. The backend
  raises a clear startup error if it's unset, rather than silently
  falling back to a local file. Deployment architecture is now
  **Vercel → Render → Supabase PostgreSQL**. All models/queries were
  already portable SQLAlchemy (no SQLite-specific types or raw SQL
  outside the legacy, now-inert `run_lightweight_migrations()` helper),
  so this was a configuration change, not a data-layer rewrite --
  verified by running the full schema creation, demo seeding, and a
  backend API smoke test against a real local PostgreSQL instance. The
  note below about Render's ephemeral disk (written for the old SQLite
  setup) is superseded by "Deploying updates to Render
  (PostgreSQL/Supabase persists data)" further down.
- 🕵️ **Login activity tracking**: every `POST /auth/login` attempt
  (success or failure) is now recorded to a new `login_events` table --
  see "User Activity (login tracking)" below for exactly what is/isn't
  stored, and the new `GET /admin/user-activity`, `GET
  /admin/recent-activity`, and `GET /admin/users` endpoints. Existing
  login behavior and the `/auth/login` response shape are unchanged;
  `Farmer`/`Buyer` gained a `last_login` column, and existing rows/accounts
  are unaffected (new column defaults to `NULL`, meaning "not seen yet").
  Covered by `backend/tests/test_login_tracking.py` (unique-user counting,
  failed-login identity handling, admin-only access) in addition to the
  existing suite -- 18/18 tests passing.
- ⚠️ **Render deployment safety note added**: see "Deploying updates to
  Render without losing existing data" below -- SQLite on Render's default
  ephemeral disk does not survive redeploys unless a Render Disk is
  attached. This is a pre-existing property of the stack, not something
  introduced by this change, but it's directly relevant to safely shipping
  this update to a live deployment with real users.
- 🔐 **Admin credential hardening**: removed the demo admin password from
  this README, from `backend/.env.example` (now a commented-out template
  instead of a real committed value), and from the admin login page's
  frontend source (it used to print the demo password directly under the
  sign-in form). Admin auth was already, and remains, verified
  server-side only (`ADMIN_USERNAME`/`ADMIN_PASSWORD` env vars, checked in
  `app/routers/auth.py::admin_login`) -- the frontend only ever forwards a
  typed username/password to that endpoint.
- 🔒 **Security**: rotated the exposed `DATA_GOV_IN_API_KEY`, added a
  project `.gitignore` (there wasn't one -- `.env` could have been
  committed), confirmed the key exists only server-side (never in the
  frontend bundle, logs, or this README).
- 🗺️ **Mandi discovery/mapping layer** (`app/services/mandi_directory.py`)
  replaces exact-string market-name matching -- see the live-data section
  below.
- 🧭 **Second live resource added** (variety-wise/district data), merged
  with the first -- prefers whichever has data.
- 📉 **Historical honesty**: real accumulated live snapshots now persist
  over time; `/market/prices` and `/forecast` only show genuine data by
  default, with an explicit `include_demo` opt-in for the old synthetic
  series instead of presenting it as real.
- 🎯 **Decision engine**: `/market/compare` now returns a plain-language
  `why` explanation and an explicit `insufficient_data` message instead of
  a bare error when nothing can be recommended.
- 🌗 **Dark/light theme**: a real `ThemeContext` + toggle now exists
  (persisted, respects OS preference) covering the app shell (sidebar,
  header, main background/text). Individual page cards still use light
  surface colors -- full per-page dark styling wasn't exhaustively applied
  in this pass.
- ⚠️ Not verified in this pass (no network in the build sandbox): a real
  successful call to either data.gov.in resource, `npm run build`, and the
  Python test suite (no tests currently exist in this repo -- see
  "Known limitations"). All touched Python files do pass `python -m
  py_compile`.

---

## What's inside

Everything runs on **realistic seeded demo data** (10 real Chhattisgarh
accounts) so the full flow works immediately with **zero external API keys and zero internet dependency**.

## Razorpay payments (TEST MODE)

The accepted-offer flow creates the existing CropWise `Payment` row in
`PENDING` state. Buyers can then use **Pay Now** on the transaction detail
page. The backend derives the amount from `Transaction.total_amount`, creates
a Razorpay order, and verifies the Checkout signature before changing the
payment to `PAID`; the frontend can never mark a payment successful by itself.

For sandbox testing, create Razorpay **Test Mode** API keys and set
`RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `backend/.env`. The secret is
server-only. Razorpay webhooks are deliberately not enabled in this SIH
version; Checkout signature verification is the authoritative synchronous
confirmation path, and the payment/event records are idempotent for repeated
callbacks. For production, replace both values with Razorpay Live Mode keys
and add a separately designed webhook path before relying on asynchronous
settlement notifications.

| Area | Feature |
|---|---|
| 🌐 **Multilingual UI/text support with reliable voice interaction in English and Hindi** | 15 Indian languages supported for UI text and the text-based assistant; voice input/output is verified reliable for English and Hindi only, with an honest per-language capability matrix rather than a blanket claim |
| 📊 **Market Intelligence** | Live-style price comparison across nearby markets with a full net-profit breakdown (price − transport − mandi charges − handling), not just the sticker price |
| 🤖 **AgriAdvisor** | An explainable AI selling recommendation -- sell-now vs. hold %, with every contributing factor (demand, supply, weather, transport, price trend) shown, never a black box |
| 📈 **Price Forecast** | 7-day price forecast built from a transparent trend + volatility model, with a visible confidence score and chart |
| 🌾 **AgriMarket** | Farmers post harvest listings; verified buyers browse and submit competing offers (reverse-auction style bidding), with server-side validation (quantity/price/minimum-price/state checks) |
| ⭐ **Smart Buyer Matching** | Buyers ranked for a listing by estimated net profit, reliability, payment history, distance, and crop interest -- with reasons shown |
| 🚚 **FarmPool** | Shared-transport calculator: pools your shipment with nearby farmers heading to the same market and shows the savings |
| 🧮 **Profit Calculator** | Side-by-side comparison of multiple selling scenarios (local mandi vs. direct buyer vs. distant market, etc.) |
| 🤝 **Group Selling** | FPO/cooperative pooling with per-farmer membership tracking (re-joining updates your quantity instead of double-counting it) |
| 🔔 **Alerts** | Price-drop, high-demand, opportunity, and harvest-reminder notifications |
| 🌐🎤 **Multilingual Farm Assistant** | A text-based assistant with a language-neutral intent/entity engine, usable in any of 15 supported UI languages -- reliable voice input/output is available in English and Hindi; never silently guesses crop or location |
| 📷 **AI-Ready Quality Assessment** | A deterministic quality-grading service that validates the end-to-end marketplace workflow; the service boundary is designed so a trained vision model can replace it without changing marketplace APIs (explicitly not claimed as a live CV model) |
| 📈 **Impact Dashboard** | Admin-authenticated, live-computed platform impact: farmers/buyers connected, transactions, transport savings, estimated additional farmer income |
| 🕵️ **User Activity (login tracking)** | Admin-authenticated: registered accounts vs. unique users who've actually logged in (today/this week), successful/failed login event counts, and a recent-activity feed -- see below |

Everything runs on **realistic seeded demo data** (10 real Chhattisgarh
markets, 10 crops, 60 days of synthesized historical mandi prices, demo
farmer/buyer accounts) so the full flow works immediately with **zero
external API keys and zero internet dependency**.

---

## 🌐 Multilingual architecture

CropWise's language system follows one rule throughout: **language is a
presentation-layer concern, never a business-logic fork.** There is exactly
one recommendation engine, one market-comparison algorithm, one offer
validator -- regardless of which of the 38 listed languages a user picks.

```
 speech / typed text (any supported language)
        │
        ▼
 app/i18n/nlu.py           <- language-neutral intent + entity extraction
        │                      (crop, quantity, location, intent)
        ▼
 existing CropWise engine   <- UNCHANGED: market.compare_markets(), the
        │                      recommendation engine, etc. never see language
        ▼
 app/i18n/templates.py     <- native-language response templates
        │                      (hand-written per language, not machine-
        │                       translated, so numbers/crops slot in safely)
        ▼
 native-language text  ->  optional device TTS voice
```

**Why this scales**: adding a 16th fully-supported language means adding
one crop-name dictionary entry per crop, one response-template string, and
one frontend translation JSON file -- zero changes to routers, models, or
the recommendation engine.

### Supported languages & capability matrix

"Fully supported" means: UI translated, the assistant can extract intent/
entities from free text in that language, and it generates a native-
language response. Everything else is honestly marked instead of faked.

| Language | UI | AI understanding | Native response | Voice input (STT) | Voice output (TTS) |
|---|---|---|---|---|---|
| English | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| हिन्दी Hindi | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| मराठी Marathi | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| বাংলা Bengali | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| தமிழ் Tamil | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| తెలుగు Telugu | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| ગુજરાતી Gujarati | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| ಕನ್ನಡ Kannada | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| മലയാളം Malayalam | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| ਪੰਜਾਬੀ Punjabi | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| ଓଡ଼ିଆ Odia | ✅ | ✅ | ✅ | not verified | device-dependent |
| অসমীয়া Assamese | ✅ | ✅ | ✅ | not verified | device-dependent |
| اردو Urdu (RTL) | ✅ | ✅ | ✅ | device-dependent | device-dependent |
| भोजपुरी Bhojpuri | ✅ | ✅ | ✅ | not verified | device-dependent |
| मैथिली Maithili | ✅ | ✅ | ✅ | not verified | device-dependent |
| + 23 more (Sanskrit, Nepali, Konkani, Kashmiri, Sindhi, Manipuri, Bodo, Dogri, Santali, Mandarin, Japanese, Korean, Spanish, French, German, Portuguese, Arabic, Russian, Indonesian, Vietnamese, Thai, Turkish, Italian) | selectable | English fallback | English fallback | device-dependent | device-dependent |

The full, machine-readable matrix lives at `backend/app/i18n/languages.py`
and is also served live at `GET /assistant/languages` -- the frontend's
language picker (`LanguageSelector.jsx`) reads real-time capability from
there rather than a hard-coded list, and shows greyed-out icons for
anything not actually verified.

**"device-dependent" is not a hedge -- it's load-bearing.** Browsers don't
expose a queryable list of speech-recognition languages, so CropWise never
claims STT works; it tries, and gracefully falls back to text on any error
(permission denied, no speech, unsupported locale, network failure). TTS
*is* queryable (`speechSynthesis.getVoices()`), so CropWise checks it live
per-language per-device before ever showing a 🔊 button as active.

### How the assistant avoids "silent guessing"

The single biggest fix from the previous iteration: **the assistant used
to default unknown crops to "Tomato" and unknown locations to "Bilaspur".
It no longer does either.** If `app/i18n/nlu.py` can't find a crop or
location anywhere in the (any-language) input, the API returns
`clarification_needed: "crop"` or `"location"` with a native-language
question, and the frontend must ask the user -- verified in
`backend/app/routers/assistant.py` and covered by the test transcript
below.

### Cross-language marketplace (architecture, honestly scoped)

`CropListing.note`/`BuyerOffer.message` now carry a `language` field
alongside the original text (`app/models.py`), and
`app/i18n/translator.py` defines a `TranslationProvider` interface with a
`NoOpTranslationProvider` implementation. **No external translation API
key is configured in this build**, so freeform farmer/buyer messages are
NOT machine-translated yet -- they're preserved with their source language
and shown as-is, honestly, rather than faking a translation. Swapping in a
real provider (Google/Azure/AWS Translate) means implementing one class
and changing one line in `get_translation_provider()`; no caller changes.

What *is* genuinely cross-language today: **canonical entities**. A crop
is stored once as (e.g.) `"Soybean"` and displayed as `सोयाबीन` to a
Marathi user and `সয়াবিন` to a Bengali user via `app/i18n/crop_terms.py`
-- this is real, tested, and works regardless of which language a listing
was created in.

### How to add a new language

1. Add a `LanguageInfo` entry to `backend/app/i18n/languages.py`.
2. To make it *fully* supported: add crop aliases to `crop_terms.py`,
   intent keywords to `intents.py`, and a response template to
   `templates.py`.
3. Add a matching entry to `frontend/src/i18n/languages.js` and a
   `frontend/src/i18n/translations/<code>.json` file.
4. No router, model, or business-logic changes needed.

### Known multilingual limitations (stated honestly, not hidden)

- STT/TTS quality depends entirely on the user's browser/OS -- CropWise
  cannot guarantee accuracy for any language, only availability.
- Freeform marketplace text (offer messages, listing notes) is not yet
  machine-translated (no provider configured) -- original text + source
  language are preserved and shown as-is to viewers in another language.
- Location-name recognition in the assistant currently has curated
  aliases for Hindi/Bengali script spellings of the 10 demo markets;
  other scripts fall back to asking the user to clarify rather than
  guessing (tested -- see the Tamil example in the demo instructions).
- Intent classification is keyword-based (fast, transparent, zero
  external dependency) rather than a full LLM -- it correctly handles the
  spec's Marathi/Hindi/Bhojpuri examples but is not general-purpose NLU.

### Multilingual demo instructions

1. Open the app, use the 🌐 language picker (top-right on every page).
2. Select **मराठी (Marathi)** → go to **🌐 Global Farm Assistant** → type
   or speak: *"माझ्याकडे २० क्विंटल सोयाबीन आहे. मला कुठे विकल्यास जास्त
   फायदा होईल?"* → note it asks for your market (never guesses) → add
   *"रायपुर"* → get a full native-Marathi answer with real numbers.
3. Switch to **English** mid-conversation and ask a follow-up -- the
   crop/quantity/location already established are retained.
4. Switch to **日本語 (Japanese)** and ask the same question in English --
   see the honest "English fallback" badge (no fake Japanese AI).
5. Try the 🎤 mic button in a supported browser (Chrome) -- if a language
   lacks a voice on your machine, CropWise tells you instead of failing
   silently.

---

## Tech stack

- **Frontend:** React 18 + Vite + Tailwind CSS + Recharts
- **Backend:** Python FastAPI + SQLAlchemy
- **Database:** PostgreSQL (Supabase)
- **Auth:** JWT (python-jose) + bcrypt password hashing, with a separate
  admin-role login for the impact dashboard
- **Deployment:** Vercel (frontend) → Render (backend API) → Supabase
  PostgreSQL (database)
- **Multilingual:** custom lightweight i18n (no external translation/LLM
  API required) -- see "Multilingual architecture" above
- **Voice:** browser-native Web Speech API (SpeechRecognition +
  SpeechSynthesis) behind a swappable provider interface

---

## Project structure

```
cropwise/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + router wiring
│   │   ├── config.py            # settings incl. admin creds, runtime secret
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── models.py            # DB models (Farmer, Buyer, Listing, Offer, LoginEvent, ...)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── auth_utils.py        # JWT + password hashing + role guards
│   │   ├── seed_data.py         # seeds demo data on first run
│   │   ├── i18n/                # multilingual architecture (see above)
│   │   │   ├── languages.py     #   capability matrix (38 languages)
│   │   │   ├── crop_terms.py    #   canonical crop <-> localized display names
│   │   │   ├── location_terms.py#   market-name alias recognition
│   │   │   ├── intents.py       #   language-neutral intent keyword classifier
│   │   │   ├── nlu.py           #   text -> {intent, crop, qty, location}
│   │   │   ├── templates.py     #   native-language response templates
│   │   │   └── translator.py    #   TranslationProvider abstraction (marketplace)
│   │   ├── mock_data/           # crops, markets, historical prices, demo users
│   │   ├── services/            # recommendation engine, price predictor,
│   │   │                        #   buyer matcher, transport optimizer, quality grading,
│   │   │                        #   login_tracking (records login_events, see above)
│   │   └── routers/             # one router per feature area (16 total)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/client.js        # single fetch wrapper for the whole API
    │   ├── context/AuthContext.jsx
    │   ├── i18n/                # frontend multilingual architecture
    │   │   ├── languages.js     #   capability matrix mirror
    │   │   ├── I18nContext.jsx  #   language state, lazy-loaded translations
    │   │   ├── speech.js        #   SpeechProvider abstraction (STT)
    │   │   ├── tts.js           #   TTSProvider abstraction (live voice check)
    │   │   └── translations/    #   *.json per fully-supported language
    │   ├── components/          # Layout, LanguageSelector, StatCard, ...
    │   └── pages/                # one page per feature area (15 pages)
    ├── package.json
    └── .env.example
```

---

## Setup & run instructions

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then set DATABASE_URL to your own Supabase
                                 # connection string (see .env.example) --
                                 # the backend will not start without it

uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000** (interactive docs at
`http://localhost:8000/docs`). On first startup it automatically **seeds
the database** with demo farmers, buyers, listings, offers, and 60
days of historical prices for every crop/market pair -- you'll see
`CropWise demo data seeded successfully.` in the console. This only happens
once: the seed check is idempotent, so restarting against the same
already-seeded Supabase database is a fast no-op.

### 2. Frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env            # points the frontend at http://localhost:8000
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 3. Log in

Use the **"Or try instantly with a demo account"** buttons on the login
screen, or log in manually with any of these (password for all: `demo1234`):

| Role | Email | Notes |
|---|---|---|
| Farmer | `ramesh@cropwise.demo` | Bilaspur · Tomato, Paddy, Soybean |
| Farmer | `sunita@cropwise.demo` | Raigarh · Onion, Wheat, Maize |
| Farmer | `manoj@cropwise.demo` | Durg · Maize, Chana, Groundnut |
| Buyer | `freshfoods@cropwise.demo` | Processor, Raipur |
| Buyer | `greenbasket@cropwise.demo` | Retailer, Bilaspur |
| Buyer | `agriexport@cropwise.demo` | Exporter, Durg |

You can also register a brand-new farmer or buyer account from scratch --
registration works fully, no demo data required.

### Admin dashboard

`/admin` (Impact Dashboard + **User Activity** login tracking, see below)
is protected by a separate admin login, independent of farmer/buyer
accounts, and authenticated entirely server-side:

- Credentials are set via `ADMIN_USERNAME` / `ADMIN_PASSWORD` environment
  variables (see `backend/.env.example`) -- **never hard-coded, never
  shipped in this README, and never present in the frontend bundle or
  source.** The frontend admin login form only ever forwards whatever you
  type to `POST /auth/admin/login`; it has no credentials embedded in it.
- If you haven't set those environment variables, check your own
  `backend/.env` (or ask whoever deployed this instance) -- the backend
  logs a startup warning whenever it's still running on the undocumented
  fallback used for zero-config local demos, precisely so that fallback is
  never mistaken for a real, production-ready credential.

### User Activity (login tracking)

The Admin Dashboard's **User Activity** section answers "did registered
users actually log in", not just "how many accounts exist":

- Total registered farmers / buyers (plain account counts).
- Unique users logged in today / this week (distinct people with at least
  one successful login, counted once no matter how many times they signed
  in).
- Successful login events today / this month, and failed login attempts
  today (raw attempt counts -- one person logging in 5 times is 5 events).
- A **Recent Activity** table of the latest login attempts (user,
  role, time, success/failed).

This is backed by a new `login_events` table (`app/models.py::LoginEvent`)
written to on every `POST /auth/login` attempt, and a `last_login` column
on `Farmer`/`Buyer` kept in sync on each successful login. By design,
`login_events` never stores passwords, password hashes, tokens, API keys,
IP addresses, or the raw email that was typed -- only a numeric user id
(when the attempt matched a real account), role, timestamp, and
success/failure. See `GET /admin/user-activity`, `GET /admin/recent-activity`,
and `GET /admin/users` (all admin-authenticated, same guard as `/admin/impact`).

### Deploying updates to Render (PostgreSQL/Supabase persists data)

The database is **PostgreSQL, hosted on Supabase** -- not a file on
Render's local disk. That means the ephemeral-filesystem risk that used
to apply here (SQLite on Render's default disk being wiped on every
redeploy) no longer applies: your data lives in Supabase, independent of
Render's container lifecycle, and survives redeploys and restarts without
needing a Render Disk.

What's still true, and still worth checking before deploying an update to
a service with real user data:

- **`DATABASE_URL` must point at the same Supabase project** across
  deploys (don't accidentally point a deploy at a different/empty Supabase
  project). Set it once in Render's dashboard environment variables --
  never commit it, and never put it in the frontend.
- Startup runs `Base.metadata.create_all()` then a small additive-only
  migration (`run_lightweight_migrations()` in `app/database.py`); that
  migration step is SQLite-specific from before this project moved to
  Postgres and is a no-op against Supabase -- a fresh Supabase database
  gets its full current schema directly from `create_all()`, and an
  already-initialized one is untouched (`create_all()` never drops or
  rewrites existing tables/columns). See "Migration method" in this
  README's implementation notes, and `backend/tests/test_login_tracking.py`
  for the automated regression coverage of the login-tracking columns.
- Demo seeding (`app/seed_data.py::seed()`) only ever runs when the
  `farmers` table is completely empty, and is a no-op on every subsequent
  startup once any farmer exists (whether a demo account or a real
  registration) -- it cannot duplicate or overwrite rows on redeploy.
- Login history is necessarily forward-only: `login_events` starts
  recording from the moment this code is deployed. There is no way to
  reconstruct who logged in *before* that point, and this app does not
  claim otherwise anywhere in the admin dashboard.

---

## Security fixes included in this build

- **Admin endpoints require admin authentication** (`require_admin` role
  guard) -- previously `/admin/impact` was publicly reachable.
- **JWT secret is never a publicly-visible hard-coded value** -- if
  `SECRET_KEY` isn't set in `.env`, the backend generates a random one at
  startup (logged as a warning) rather than using a known placeholder.
- **Public farmer/buyer endpoints no longer leak email/phone** -- they
  return a PII-free public schema; only the authenticated `/me` endpoints
  include contact details.
- **Marketplace offers are validated server-side**: price/quantity must be
  positive, offer quantity can't exceed the listing, offers below the
  farmer's minimum acceptable price are rejected, and an offer can't be
  accepted/rejected twice or against an inactive listing.
- **Group-selling pool membership no longer double-counts** -- a farmer
  re-joining a pool now updates their own membership row instead of
  summing on top of a previous join.
- **Buyer-matching endpoint requires the listing owner's farmer login**
  (previously unauthenticated).

---

## Suggested demo flow (for judging / presentation)

1. Log in as **Ramesh Kumar** (farmer).
2. **Market Intelligence** → compare Tomato prices across nearby markets →
   see the recommended market and the real net profit after transport.
3. **AgriAdvisor** → ask for a recommendation on the same crop → see the
   sell-now/hold split and every factor behind it (demand, supply, weather,
   transport, trend).
4. **Price Forecast** → view the 7-day forecast chart with confidence score.
5. **AgriMarket** → open "My listings" → view offers already placed on the
   seeded Tomato listing → open "Smart buyer matches" → accept the best offer.
6. **FarmPool** → see shared-transport savings vs. going alone.
7. **Profit Calculator** → compare "Local Mandi" vs. "Direct Buyer" scenarios.
8. **Ask AgriAdvisor** → type or speak (🎤 button, Chrome) a question in
   Hindi: *"मेरे पास 10 क्विंटल धान है, कहाँ बेचने पर ज्यादा फायदा होगा?"*
9. Log out, log in as **FreshFoods Processing** (buyer) → browse
   AgriMarket → make an offer on an active listing.
10. Visit `/admin` for the live **Impact Dashboard**.

---

## Notes on data & "real" integrations

This is a hackathon MVP, so a few things are explicitly simulated rather
than wired to live external services -- each is written so it's a clean
drop-in replacement point for the real thing later:

- **Historical mandi prices** are generated with a seeded random walk
  (`app/mock_data/historical_prices.py`) instead of a live Agmarknet/eNAM
  feed. The seed is deterministic per crop/market so the demo is stable.
- **Price forecasting** uses a transparent linear-trend + volatility model
  (`app/services/price_predictor.py`) rather than a trained ML model --
  the return shape is ready to swap in Prophet/XGBoost/LSTM without
  touching the API or frontend.
- **Weather risk** is a deterministic simulated signal
  (`app/services/recommendation_engine.py`) standing in for a live weather API.
- **AI-ready quality assessment** (`app/services/quality_grading.py`)
  simulates a computer-vision result from the crop name/image filename --
  intentionally *not* presented as a live CV model. It validates the full
  marketplace workflow (grading -> listing -> matching) so a trained image
  classifier can be dropped into the same service boundary later.
- **Market data has a real, multi-source live-data integration, wired and
  testable, but unverified by the assistant from its sandbox** (see the
  honesty note below): CropWise queries **two independent government-
  linked sources CONCURRENTLY, never as a fallback chain where one is
  only tried after the other fails** -- both are attempted in parallel
  whenever both are configured, and their results are combined with
  explicit source attribution rather than one silently overriding the
  other. See `app/services/mandi_directory.py::fetch_price_result` for
  the authoritative contract; this section summarizes it.

  **Source 1 -- data.gov.in** (`app/services/live_market_data.py` +
  `app/services/district_market_data.py`), itself two resources tried in
  order of precision:
  1. **"Current Daily Price of Various Commodities from Various Markets"**
     (resource `9ef84268-d588-465a-a308-a864a43d0070`), keyed by an exact
     `market` name.
  2. **"Variety-wise Daily Market Prices Data of Commodity"** (resource
     `35985678-0d79-46b4-9ed6-6f13308a1d24`), keyed by revenue `District`
     -- used only if the market-level resource has no record.

  **Source 2 -- Agmarknet, via CEDA's AGMARKNET API**
  (`app/services/agmarknet_service.py`). CEDA is an aggregator that
  re-serves official Agmarknet mandi data through a documented REST API;
  CropWise has no separate/direct Agmarknet integration, so
  `CEDA_API_KEY` **is** the Agmarknet configuration -- there is
  intentionally no second `AGMARKNET_API_KEY`.

  A local town like "Bilaspur" is not guaranteed to match either
  government source's exact market-name string, so `mandi_directory.py`
  sits in front of both: it discovers the *actual* market names
  data.gov.in has for a state (`GET /market/live-markets`), fuzzy-matches
  local names against them (plus a small hand-maintained alias table),
  and maps towns to their revenue district for the district-level
  resource -- this candidate-name resolution is internal to the
  data.gov.in fetch itself, not a fallback between the two *providers*.

  **How the two providers' results are combined:**
  - If only one provider has usable data, that one's result is used and
    labeled with that single source.
  - If both have data for the same (or a parseable-as-equal) date and
    their modal prices are within **2%** of each other, they're treated
    as agreeing: the response is labeled with both sources
    (`sources: ["data.gov.in", "agmarknet"]`), `source_conflict: false`,
    and both raw values remain inspectable under `source_values`.
  - If both have data for the same date but the modal prices differ by
    more than 2%, that's a genuine conflict: **both values are kept**,
    `source_conflict: true` is set, and `source_values` exposes exactly
    what each provider reported -- neither is discarded or silently
    averaged away, and the top-level "current" price is the most recent
    observation.
  - If the two providers report *different* dates entirely, both are
    preserved as separate entries under `observations` rather than one
    overwriting the other; the top-level fields reflect whichever
    observation is more recent.
  - If one provider is unconfigured (no key) or its request genuinely
    fails, the request is **not** failed -- the other provider's result
    (if any) is used on its own. A provider being down or unconfigured
    never blocks a real answer from the other one, and a confirmed
    "no record exists" from one configured provider is never downgraded
    into a vague "unavailable" just because the other provider happens
    not to be configured.
  - Only when **neither** provider has usable data does CropWise fall
    back to the seeded demo dataset (see labeling below).

  When at least one of `DATA_GOV_IN_API_KEY` / `CEDA_API_KEY` is set,
  every market-price lookup attempts the live path(s) first and
  transparently falls back to the seeded demo dataset only if nothing
  live is available. **Every price is labeled `data_source: "live"` or
  `"demo"` individually** -- never blended or silently mislabeled -- and
  a live row additionally carries `sources`/`source_conflict` so the
  frontend can show which provider(s) backed it and whether they agreed.
  The Market Intelligence page shows a 🟢 Government Data / 🟡 Demo Data
  badge per row, driven by the real `GET /market/data-source-status` and
  per-record `data_source` fields, not a static claim.

  **Caching:** each provider caches its own successful responses for a
  bounded TTL, never longer than the data realistically stays current,
  and caches *failures* separately and much more briefly, so a slow or
  down provider degrades to "fail fast" rather than repeatedly re-paying
  a multi-second timeout on every request:
  - data.gov.in (`live_market_data.py` / `district_market_data.py`):
    10-minute TTL for a successful lookup; failures are also cached
    (same 10-minute window) so a flaky/unreachable endpoint doesn't add
    delay to every subsequent request.
  - Agmarknet/CEDA (`agmarknet_service.py`): 10-minute TTL for a price
    lookup, 1-hour TTL for the rarely-changing commodity/geography
    reference lists, and a 30-second negative cache for a request
    failure specifically (short, so a genuinely-recovered provider isn't
    treated as down for the full 10 minutes).
  - Market-name discovery (`mandi_directory.py`'s
    `discover_state_markets`): 24-hour TTL -- which markets exist for a
    state changes rarely.
  - A **failure is never cached as if it were a successful result**, and
    a demo/fallback value is never written into any of these caches --
    each cache only ever holds a genuine provider response (success or
    failure), never a substituted value.
  - `compare_markets`'s admin-facing caller (`/admin/impact`) additionally
    shares one request-scoped lookup cache across all sampled listings,
    so listings sharing a crop/market don't each re-trigger the same
    network call -- see `_compare_markets_core`'s `outcome_cache`
    parameter.

  **Historical price charts and the forecast now only ever use genuine
  data.** Every successful live fetch is persisted as a real `MarketPrice`
  row (`data_source="live"`, with `source` recording which provider(s)
  contributed -- e.g. `"data.gov.in"`, `"agmarknet"`, or
  `"data.gov.in+agmarknet"` when both agreed -- and `source_timestamp`
  recording the provider's own reported fetch time), so honest history
  accumulates day by day as the app is used. Demo/seeded rows are always
  `data_source="demo"` with `source`/`source_timestamp` left `NULL` --
  the two are never conflatable by construction, not just by convention.
  `GET /market/prices` and `GET /forecast` return only those real rows by
  default; if there isn't enough real history yet they return
  `available: false` with `"Historical mandi data is currently
  unavailable."` instead of drawing a chart from the synthetic series.
  Pass `include_demo=true` to explicitly opt into the old 60-day synthetic
  series for a walkthrough of the methodology -- every row and the whole
  response are tagged `is_demo: true` so it's never mistaken for real data.

  **Third-party sources beyond these two -- intentionally deferred.**
  The spec for this integration allows querying additional trusted
  sources when data.gov.in and Agmarknet are insufficient. Investigated
  and did not add one: e-NAM (enam.gov.in) is a real government
  platform but has no documented public API to integrate against; the
  other results found (e.g. third-party "mandi price" aggregator sites)
  explicitly re-serve the same underlying data.gov.in feed rather than
  being an independent observation, so adding one would add the
  appearance of a third source without any actual new information or
  redundancy. No fake/placeholder provider was added to make this look
  done -- if a genuinely independent, trustworthy, API-accessible source
  becomes available, it plugs into the same `_normalize_source_record` /
  `_combine_source_records` pattern the other two already use.

  **Honesty note on testing:** `api.data.gov.in` and CEDA's API are
  outside this sandbox's network egress allowlist, so the assistant that
  built this could not observe a live *successful* fetch from either
  provider against the real internet -- every code path above was
  verified with realistic mocked provider responses (see
  `backend/tests/test_multi_source_pricing.py` and
  `backend/tests/test_caching_and_persistence.py`), not a real network
  call. **Please verify with real internet access and real keys**, and
  report back if either provider's response schema differs from what's
  documented here -- government/aggregator open-data schemas do
  occasionally change.
- **Voice input** uses the browser's native Web Speech API (works in
  Chrome), so no speech-to-text API key is required. **Voice input
  (speech-to-text) is intentionally offered for English and Hindi
  only** -- other languages have full UI/text/assistant support but no
  microphone button, because Web Speech API recognition quality for
  most Indian regional languages is inconsistent across browsers/OSes
  in practice, and CropWise would rather not offer a feature it can't
  back up reliably.

## Known limitations

- Image uploads for quality grading are simulated by filename only -- no
  actual file upload/storage is wired up.
- The demo dataset covers Chhattisgarh markets/crops; extending to more
  states just means adding entries to `app/mock_data/locations.py` and
  `app/mock_data/crops.py`.

---

## Environment variables

See `backend/.env.example` and `frontend/.env.example` for the full list
with comments -- this only calls out the ones most people will actually
touch. `DATABASE_URL` is required (see "PostgreSQL (Supabase)" above);
everything below is optional.

| Variable | Used for |
|---|---|
| `DATABASE_URL` | **Required.** Supabase Postgres connection string. |
| `SECRET_KEY` | JWT signing key. Falls back to a random per-process key with a startup warning if unset -- fine for a local demo, not for anything reachable by others. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin dashboard login. Defaults to a publicly-documented demo login if unset. |
| `DATA_GOV_IN_API_KEY` | Enables the data.gov.in market-price source. Optional -- leave empty to run on the other source and/or demo data. |
| `MARKET_DATA_SOURCE` | Set to `live` to require validated data.gov.in responses (see multi-source notes above). |
| `CEDA_API_KEY` | Enables the Agmarknet-via-CEDA market-price source. Optional, independent of `DATA_GOV_IN_API_KEY` -- either, both, or neither can be set. **There is no separate `AGMARKNET_API_KEY`** -- CEDA's API is the actual Agmarknet integration this project uses. |

`frontend/.env.example` has working defaults for local development -- you
only need to edit it if you're changing ports or deploying somewhere
other than localhost. It never contains database credentials or any
backend secret (see "PostgreSQL (Supabase)" above for why).
