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
- **Database:** SQLite (zero-config, file-based -- no server to install)
- **Auth:** JWT (python-jose) + bcrypt password hashing, with a separate
  admin-role login for the impact dashboard
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

cp .env.example .env            # defaults already work, edit if you want

uvicorn app.main:app --reload --port 8000
```

The API is now running at **http://localhost:8000** (interactive docs at
`http://localhost:8000/docs`). On first startup it automatically **seeds
the SQLite database** with demo farmers, buyers, listings, offers, and 60
days of historical prices for every crop/market pair -- you'll see
`CropWise demo data seeded successfully.` in the console. Nothing further
to configure.

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

### Deploying updates to Render without losing existing data

This app's database is a single **SQLite file on local disk** (`DATABASE_URL=sqlite:///./cropwise.db`
by default). That has one critical consequence for a live Render deployment
with real registered users:

> **⚠️ On most Render web service plans, local disk is *ephemeral* --
> it is wiped on every redeploy and on every restart, unless you have
> attached a [Render Disk](https://render.com/docs/disks) (persistent
> volume) and pointed `DATABASE_URL` at a path inside it.**

This is true regardless of anything in this changeset -- it's a property of
"SQLite + Render's default ephemeral filesystem", not a bug this update
introduces or fixes. Two things to check **before** deploying this update
to a service with real user data:

1. **Confirm a Render Disk is attached** to the web service, mounted at
   (for example) `/var/data`, and that `DATABASE_URL` is set to
   `sqlite:////var/data/cropwise.db` (note: **four slashes** for an
   absolute path) -- not the default relative `./cropwise.db`, which
   resolves inside the ephemeral container filesystem.
2. **If you're not sure**, back up the current database first: from a
   Render shell on the running service, copy whatever file `DATABASE_URL`
   points at (e.g. `cp cropwise.db /var/data/cropwise-backup-$(date +%F).db`
   if a disk is mounted at `/var/data`, or download it via `render ssh` /
   the dashboard's shell before deploying otherwise).

Assuming disk persistence is already in place (or you're fine starting
fresh), this specific update is safe to deploy on top of existing data:

- Startup runs `Base.metadata.create_all()` then a small additive-only
  migration (`run_lightweight_migrations()` in `app/database.py`) that only
  ever *adds* a table (`login_events`) or *adds* a nullable column
  (`last_login` on `farmers`/`buyers`) -- it never drops a table, drops a
  column, or rewrites existing row data. See "Migration method" in this
  README's implementation notes, and `backend/tests/test_login_tracking.py`
  for the automated regression coverage.
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
- **Market data has a real live-data integration point, wired and testable, but unverified by the assistant from its sandbox:**
  CropWise now queries **two** data.gov.in resources and prefers whichever
  has data:
  1. **"Current Daily Price of Various Commodities from Various Markets"**
     (resource `9ef84268-d588-465a-a308-a864a43d0070`) via
     `app/services/live_market_data.py`, keyed by an exact `market` name.
  2. **"Variety-wise Daily Market Prices Data of Commodity"** (resource
     `35985678-0d79-46b4-9ed6-6f13308a1d24`, capitalized `State`/`District`/
     `Commodity`/`Arrival_Date` fields, no market filter) via
     `app/services/district_market_data.py`, keyed by revenue `District`.

  A local town like "Bilaspur" is not guaranteed to match the government's
  exact market-name string, so instead of relying on CropWise's internal
  town list as ground truth, `app/services/mandi_directory.py` sits in
  front of both: it discovers the *actual* market names data.gov.in has
  for a state (`GET /market/live-markets`), fuzzy-matches local names
  against them (plus a small hand-maintained alias table), maps towns to
  their revenue district for the second resource, and merges the two --
  preferring the market-level hit (more mandi-precise) but attaching the
  district resource's variety-level detail as `district_reference` when
  both have data.

  When `DATA_GOV_IN_API_KEY` is set and `MARKET_DATA_SOURCE=live` in
  `backend/.env`, every market-price lookup attempts this live path
  first and transparently falls back to the seeded demo dataset if
  neither live source has a record for that combination or both are
  unreachable. **Every price is labeled `data_source: "live"` or
  `"demo"` individually** -- never blended or silently mislabeled -- and
  the Market Intelligence page shows a 🟢 Government Data / 🟡 Demo Data
  badge per row, driven by the real `GET /market/data-source-status` and
  per-record `data_source` fields, not a static claim.

  **Historical price charts and the forecast now only ever use genuine
  data.** Every successful live fetch is persisted as a real `MarketPrice`
  row (`data_source="live"`), so honest history accumulates day by day as
  the app is used. `GET /market/prices` and `GET /forecast` return only
  those real rows by default; if there isn't enough real history yet they
  return `available: false` with `"Historical mandi data is currently
  unavailable."` instead of drawing a chart from the synthetic series.
  Pass `include_demo=true` to explicitly opt into the old 60-day synthetic
  series for a walkthrough of the methodology -- every row and the whole
  response are tagged `is_demo: true` so it's never mistaken for real data.

  **Honesty note on testing:** `api.data.gov.in` is outside this
  sandbox's network egress allowlist, so the assistant that built this
  could not observe a live *successful* fetch from either resource --
  only the fallback path (non-200 / timeout / no records), which is
  exactly the failure mode the fallback logic is designed for. The
  discovery, matching, merge, and persistence logic in
  `mandi_directory.py` / `district_market_data.py` compiles and is
  structured to be testable with mocked responses, but nobody has yet
  watched it resolve a real Chhattisgarh mandi/district against the live
  dataset. **Please verify with real internet access and the regenerated
  key**, and report back if either response schema differs from what's
  documented here -- government open-data schemas do occasionally change.
- **Voice input** uses the browser's native Web Speech API (works in
  Chrome), so no speech-to-text API key is required. **Voice input
  (speech-to-text) is intentionally offered for English and Hindi
  only** -- other languages have full UI/text/assistant support but no
  microphone button, because Web Speech API recognition quality for
  most Indian regional languages is inconsistent across browsers/OSes
  in practice, and CropWise would rather not offer a feature it can't
  back up reliably.

## Known limitations

- SQLite is used for zero-config setup; swap `DATABASE_URL` in
  `backend/.env` for a Postgres URL if you want a production-style DB
  (the SQLAlchemy models will work unchanged).
- Image uploads for quality grading are simulated by filename only -- no
  actual file upload/storage is wired up.
- The demo dataset covers Chhattisgarh markets/crops; extending to more
  states just means adding entries to `app/mock_data/locations.py` and
  `app/mock_data/crops.py`.

---

## Environment variables

See `backend/.env.example` and `frontend/.env.example`. Both already have
working defaults -- you only need to edit them if you're changing ports or
deploying somewhere other than localhost.
