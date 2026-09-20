# CropWise

**A decision-support platform for Indian farmers — not another mandi-price app.**

CropWise doesn't just show farmers a market price. It tells them their actual
expected profit after transport and other costs, compares that across nearby
markets, and connects them directly with a matching buyer. This README is
generated from an audit of the actual source code in this repository — every
claim below is backed by a file, a test, or a build log, not by the product
pitch.

---

## Overview

CropWise is a FastAPI + PostgreSQL backend and a React (Vite) frontend, built
for the Smart India Hackathon problem statement on market linkages and price
discovery for farmers. It combines government mandi-price data with a
transport-cost model to answer one question a plain price ticker can't:
**after you pay to move your crop, which market actually nets you the most?**

## Problem

Farmers commonly sell to the nearest mandi or the first buyer who calls,
because comparing markets requires data (today's prices, several mandis away)
they don't have in a usable form, and even when prices are visible, farmers
rarely calculate the transport cost against the price gap — so a
higher-priced market 40 km further away can quietly be the worse deal.

## Solution

CropWise's core loop is:

```
Add produce  →  Compare nearby markets  →  Net realisation (price − transport − fees)
     →  Best Selling Option  →  Find a buyer  →  Arrange transport  →  Get paid
```

Every step is backed by a real, runnable feature in this repo — see the
Implementation Status table below for exactly which parts are live data,
which are a working rules-based engine, and which are demo/seeded for
presentation purposes.

## Key Features

- **Market Intelligence** — live government mandi prices (data.gov.in +
  AGMARKNET/CEDA) with an honest LIVE/DEMO status on every figure.
- **Net-realisation "Best Selling Option"** — the platform's core
  differentiator: ranks markets by *price minus a modelled transport cost*,
  not price alone.
- **Price Forecast** — a 7-day forecast with a disclosed accuracy backtest,
  not a black-box number.
- **AgriAdvisor** — a rule-based, multilingual (Hindi/English) explainable
  recommendation assistant. Not a general-purpose LLM — see
  [Tech Stack](#tech-stack) below.
- **Marketplace & buyer matching** — buyer demand listings, an offer flow,
  and a buyer-verification workflow (CropWise's own admin review — not a
  government or eNAM verification).
- **FarmPool** — splits transport cost across nearby farmers heading to the
  same market, using a realistic (diesel/vehicle-class/driver/toll) costing
  model, not a flat rate.
- **Group Selling** — pools produce through an FPO/cooperative for stronger
  bulk-negotiation pricing.
- **Transport Coordination** — request creation, vehicle-type selection,
  and status tracking for a crop lot's trip.
- **Storage Marketplace, Notifications, Grievances, Transaction history,
  Quality grading from an uploaded photo** (a heuristic pixel/colour
  analyser — not a trained computer-vision model), **and an admin
  dashboard.**

## How CropWise Works

1. **Add Produce** — a farmer creates a crop lot (crop, quantity, quality).
2. **Market Analysis** — CropWise compares nearby markets using live or demo
   price data plus a distance-based transport estimate.
3. **Best Selling Option** — the market with the highest *net* return is
   surfaced, with the price/transport/fee breakdown shown, not hidden.
4. **Find Buyer** — the farmer reviews buyer demands or offers and accepts one.
5. **Create & Ship** — a transport request is created and tracked to delivery.
6. **Payment Received** — a payment record is tracked through to completion.

## Crop Prices / Market Intelligence

This is the most scrutinised part of the codebase, so it's worth being exact
about what's real:

- **Primary source:** `data.gov.in`'s *"Current Daily Price of Various
  Commodities from Various Markets (Mandi)"* dataset
  (`backend/app/services/live_market_data.py`), queried live via `httpx`.
- **Secondary source:** AGMARKNET data via the CEDA (Ashoka University) API
  (`backend/app/services/agmarknet_service.py`), queried **concurrently**
  with the primary source, with basic conflict detection between the two.
- **Every price record carries:** `source`, `source_timestamp`/observed
  date, `fetched_at`, and a `data_source` flag distinguishing `live` from
  `demo`. The UI is required to show this rather than a bare number.
- **Caching:** short-TTL in-memory caching so a burst of farmer requests
  doesn't hammer the government API for the same crop/market.
- **Fallback:** when the live sources are unreachable or have no record for
  a crop/market, CropWise falls back to a **seeded, deterministic synthetic
  price series** (12 crops × 20 markets across Chhattisgarh and Maharashtra)
  and labels it as demo data — it does not silently show a stale or invented
  number as live.
- **Verified in this audit:** outbound network access to `data.gov.in`/CEDA
  is not available from the environment this audit ran in, so live
  ingestion itself could not be exercised here; the dual-source fetch,
  caching, and LIVE/DEMO labelling logic were verified by reading the code
  and its test suite, not by watching a live request succeed. Do not take
  this README as confirmation that a live fetch was observed in this pass.
- **Not implemented:** a persistent background sync job that ingests and
  stores official records ahead of time (the current design fetches
  on-demand per request, cached briefly).

## Architecture

```
┌──────────────┐      HTTPS/JSON       ┌────────────────────┐
│ React (Vite) │ ───────────────────▶  │ FastAPI backend     │
│ 25 pages     │ ◀───────────────────  │ 26 routers          │
└──────────────┘                       └─────────┬───────────┘
                                                  │ SQLAlchemy
                                                  ▼
                                        ┌────────────────────┐
                                        │ PostgreSQL(Supabase)│
                                        │ 20 tables            │
                                        └────────────────────┘
        External:  data.gov.in  ·  CEDA/AGMARKNET  ·  Open-Meteo (weather)
```

Diagrams from an earlier project write-up (architecture, workflows, ER
diagram, data flow) are kept in
[`research paper and diagrams/`](research%20paper%20and%20diagrams/) for
reference; they were not re-verified line-by-line as part of this audit.

## Tech Stack

**Backend:** FastAPI, SQLAlchemy 2.0, PostgreSQL (psycopg2), Pydantic v2,
JWT auth (python-jose + passlib/bcrypt), httpx, Pillow, pytest.
**Frontend:** React 18, Vite, Tailwind CSS, react-router-dom, Recharts,
lucide-react icons. No axios — a thin `fetch` wrapper in `src/api/client.js`.
**No ML/LLM framework is present anywhere in this codebase** (no OpenAI/
Anthropic/TensorFlow/PyTorch/scikit-learn import exists) — the "AI" features
are rule-based or statistical, and say so in their own code comments.

## Project Structure

```
backend/
  app/
    routers/       26 route modules (auth, market, transport, payments, …)
    services/      live_market_data, agmarknet_service, transport_optimizer,
                   recommendation_engine, price_predictor, quality_grading, …
    models.py      20 SQLAlchemy models
    i18n/           server-side intent phrasing for the rule-based advisor
  tests/           13 test files, 113 tests
frontend/
  src/
    pages/         25 route-level pages
    components/
    i18n/
      translations/  15 locale JSON files
research paper and diagrams/   architecture diagrams, prior write-ups
screenshots/                    real, dated app screenshots (see below)
```

## Implementation Status

| Feature | Status | Evidence / Notes |
|---|---|---|
| Authentication | **Implemented** | JWT, bcrypt password hashing, farmer/buyer/admin roles (`auth.py`, `auth_utils.py`) |
| Crop Prices / Market Intelligence | **Implemented (live) + Demo fallback** | Dual live source + honest LIVE/DEMO labelling; live fetch not exercised in this audit (network-restricted environment) |
| Market Comparison / Net Realisation | **Implemented** | `market.py::compare_markets`, transport cost folded into the ranking |
| Best Selling Option | **Implemented** | Built on the same comparison + `recommendation_engine.py` |
| Transport cost model | **Implemented, realistic** | Vehicle-class/diesel-price/driver/toll model (`transport_optimizer.py`), not a flat rate |
| Transporter accounts / quote negotiation | **Not implemented** | No transporter role exists in `auth_utils.py`; no quote/negotiation fields on `TransportRequest` in this snapshot |
| FarmPool (shared transport) | **Implemented, demo-labelled** | Real cost-split math; nearby-farmer profiles are explicitly `pool_partners_are_simulated=True` |
| Group Selling (FPO pooling) | **Implemented** | `group_selling.py` + `GroupSelling.jsx` |
| Buyer discovery / matching | **Implemented** | `buyer_matcher.py`, `matching.py`, `buyer_demands.py` |
| Buyer verification | **Implemented (platform-level)** | 5-state admin review workflow; explicitly **not** a government/eNAM verification |
| AgriAdvisor | **Implemented, rule-based** | Multilingual intent engine over real backend data; not an LLM |
| Ask Assistant | **Implemented, rule-based** | Same intent engine, chat-style UI |
| Price Forecast | **Implemented, statistical** | Backtested accuracy reported in-app, not a trained ML model |
| Quality grading | **Implemented, heuristic** | Real uploaded-image pixel/colour/texture analysis — not a trained CV model |
| Payments | **Simulated (no real gateway)** | Backend is a PENDING→INITIATED→PAID tracker only. **The frontend has a "Pay Now" button that calls a Razorpay checkout flow and backend endpoints (`/payments/create-order`, `/payments/{id}/verify`) that do not exist in the backend** — this is a real, unresolved bug, not a design choice. See [Current Limitations](#current-limitations). |
| Transactions / receipts | **Partially implemented** | Transaction lifecycle and history exist; no dedicated receipt/PDF or hash-verification endpoint was found in this snapshot |
| Storage Marketplace | **Demo/mock** | Facilities are explicitly labelled `is_demo=True` |
| Notifications | **Implemented** | Real, persisted per-user notifications (`notifications.py`) |
| Grievances | **Implemented** | Farmer-raised grievance records with status tracking |
| Weather | **Implemented (live) + Demo fallback** | Open-Meteo integration with a deterministic fallback when unavailable |
| Admin dashboard | **Implemented** | Buyer verification review, user activity/login tracking |
| i18n / Localisation | **Partially implemented** | See the dedicated section below — real infrastructure, incomplete coverage |

## Backend

- 26 FastAPI routers, 20 SQLAlchemy models, PostgreSQL-only in production
  (there is no SQLite fallback in the app itself — `DATABASE_URL` must be a
  real Postgres/Supabase instance, or the app refuses to start).
- **113 backend tests, all passing** in this audit
  (`DATABASE_URL="sqlite:///:memory:" pytest`, SQLite in-memory used only
  for test isolation).
- No ORM migration framework (no Alembic) — schema changes rely on
  `create_all()` at startup plus a small hand-written "add column if
  missing" helper for columns added after the database was first
  provisioned.

## Frontend

- 25 route-level pages, React 18 + Vite + Tailwind, dark/light theme
  support throughout.
- `npm run build` **succeeds** (verified in this audit): ~921 KB main
  bundle (236 KB gzipped) plus one lazy-loaded chunk per locale. Vite warns
  about the >500 KB main chunk; this is a real, unaddressed
  code-splitting opportunity, not a build error.
- No frontend automated test suite is configured (no test script in
  `package.json`).

## i18n / Localisation

CropWise supports 15 locales (`en, hi, mr, as, bho, bn, gu, kn, mai, ml,
or, pa, ta, te, ur`) through a single flat-key JSON dictionary per locale
with a graceful `locale → English → raw key` fallback chain, so a missing
translation never breaks the page — it just displays in English.

**Real, exact key counts from this audit** (English is the canonical key set):

| Locale | Keys present | Coverage |
|---|---:|---:|
| en (English) | 1072 / 1072 | 100% |
| hi (Hindi) | 445 / 1072 | ~41.5% |
| mr (Marathi) | 245 / 1072 | ~22.9% |
| as, bho, bn, gu, kn, mai, ml, or, pa, ta, te, ur (12 locales) | 157 / 1072 each | ~14.6% each |

**Overall coverage across all 15 locales: ~22.7%** (3,646 of 16,080
possible translated slots). Do not read this app as "multilingual" in the
sense of every screen being fully translated in every language — English
and, to a lesser extent, Hindi and Marathi are the only locales with
meaningful depth today; the other 12 cover only core
navigation/authentication strings. A screenshot in this repository
(`Screenshot 2026-09-11 010111.png`) also shows a raw, untranslated
`landing.journeyHeading`-style key rendered on screen at one point in
development — evidence that key-lookup gaps have been a real, observed
issue, not just a theoretical one. A later screenshot from the same session
shows it fixed for that specific page.

**What genuinely works:** the language selector, the fallback chain, and
full-depth English/Hindi/Marathi on the main pages exercised in this audit.
**What's incomplete:** deep translation for the other 12 locales, and a
hardcoded-string sweep — a simple heuristic scan run as part of this audit
(looking for plain JSX text not passed through `t()`) found **73 candidate
lines across 6 files** (`AIAdvisor.jsx`, `AskAssistant.jsx`, `Landing.jsx`,
`PriceForecast.jsx`, `ProfitCalculator.jsx`, `Layout.jsx`). Not every hit is
a real gap — the scan also flags brand names, units, and statistical
abbreviations (`MAE`, `RMSE`) that are legitimately left untranslated — but
it indicates real remaining work, concentrated in `AIAdvisor.jsx`.

## API / Integrations

| Integration | Status |
|---|---|
| data.gov.in (mandi prices) | Implemented; live reachability not verified in this audit's network-restricted environment |
| AGMARKNET via CEDA | Implemented as a secondary source, same caveat |
| Open-Meteo (weather) | Implemented, free tier, no API key required |
| Razorpay (payments) | **Not implemented on the backend** despite frontend code that assumes it exists (see Current Limitations) |
| Any LLM/AI API | **Not used anywhere in this codebase** |

## Database

PostgreSQL (Supabase-hosted in the reference deployment). 20 tables covering
users (farmers/buyers), crop listings and lots, buyer demands and offers,
transactions, transport requests, storage bookings, group-selling pools,
buyer verification, grievances, notifications, and market-price history.
`backend/.env.example` documents the required connection variables; no real
credentials are present in this repository.

## Current Limitations

- **Payment checkout is broken end-to-end.** `TransactionDetail.jsx`'s
  buyer-facing "Pay Now" button loads the Razorpay Checkout script and
  calls backend endpoints (`create-order`, `verify`, `cancel`, `failed`)
  that do not exist anywhere in `backend/app/routers/payments.py`. The
  actual working payment path is a simulated
  initiate → confirm-received flow with no real gateway. This needs a real
  fix (either wire up Razorpay server-side or remove the dead client code),
  not a description change.
- **No transporter role.** There is no way for an actual transporter to log
  in, see requests, or submit a quote; transport cost is currently an
  estimate only.
- **i18n coverage is shallow outside English/Hindi/Marathi**, as detailed
  above.
- **Live market data reachability was not verified in this audit** — the
  code path exists and is tested with mocked responses, but this pass ran
  in a network-restricted sandbox and could not confirm a real government
  API response end-to-end.
- **No receipts, PDF export, or hash-based integrity verification** was
  found for transactions in this snapshot.
- **No ORM migration tool (Alembic)** — schema evolution is handled by a
  bespoke "add column if missing" helper, which works but doesn't track
  history the way a real migration tool would.

## What Is Left

### Remaining for MVP
- Fix or remove the broken Razorpay checkout path.
- Decide on and build (or explicitly drop) transporter accounts and
  quote/negotiation, since transport cost is currently an estimate only.
- Verify live market-data ingestion against the real data.gov.in/CEDA APIs
  from a network-unrestricted environment.

### Important Improvements
- Frontend automated tests (none exist today).
- Code-splitting the frontend's >500 KB main bundle.
- A real migration tool instead of the hand-rolled column-adding helper.
- A systematic hardcoded-string sweep and deeper translation pass for the
  9 shallow-coverage locales.

### Future Features
- Receipts / exportable transaction documents.
- A genuine transporter marketplace (accounts, ratings, negotiation).
- Background/scheduled market-data ingestion rather than on-demand fetch.

## Screenshots

<p align="center">
  <img src="screenshots/Screenshot%202026-09-07%20225620.png" width="49%" alt="CropWise landing page, light theme" />
  <img src="screenshots/Screenshot%202026-09-11%20010200.png" width="49%" alt="CropWise landing page, dark theme" />
</p>

### Desktop / Laptop

<table>
<tr>
<td align="center" width="50%">
<img src="screenshots/Screenshot%202026-09-13%20132443.png" width="100%" alt="Farmer dashboard with Best Selling Opportunity" /><br/>
<sub><b>Farmer Dashboard — Best Selling Opportunity</b></sub>
</td>
<td align="center" width="50%">
<img src="screenshots/Screenshot%202026-09-09%20091208.png" width="100%" alt="Farmer dashboard in Marathi" /><br/>
<sub><b>Farmer Dashboard (Marathi)</b></sub>
</td>
</tr>
<tr>
<td align="center">
<img src="screenshots/Screenshot%202026-09-07%20225932.png" width="100%" alt="Price forecast page" /><br/>
<sub><b>Price Forecast</b></sub>
</td>
<td align="center">
<img src="screenshots/Screenshot%202026-09-07%20225952.png" width="100%" alt="Profit calculator page" /><br/>
<sub><b>Profit Calculator</b></sub>
</td>
</tr>
<tr>
<td align="center">
<img src="screenshots/Screenshot%202026-09-13%20152347.png" width="100%" alt="FarmPool shared transport page" /><br/>
<sub><b>FarmPool (shared transport)</b></sub>
</td>
<td align="center">
<img src="screenshots/Screenshot%202026-09-07%20230030.png" width="100%" alt="Storage marketplace page" /><br/>
<sub><b>Storage Marketplace</b></sub>
</td>
</tr>
</table>

### Tablet

<table>
<tr>
<td align="center">
<img src="screenshots/Screenshot%202026-09-07%20232042.png" width="100%" alt="Buyer demands list, tablet width" /><br/>
<sub><b>Buyer Demands</b></sub>
</td>
<td align="center">
<img src="screenshots/Screenshot%202026-09-07%20232143.png" width="100%" alt="Global Farm Assistant, tablet width" /><br/>
<sub><b>Global Farm Assistant</b></sub>
</td>
<td align="center">
<img src="screenshots/Screenshot%202026-09-13%20152910.png" width="100%" alt="Group Selling, tablet width" /><br/>
<sub><b>Group Selling</b></sub>
</td>
<td align="center">
<img src="screenshots/Screenshot%202026-09-13%20153534.png" width="100%" alt="Transport coordination, tablet width" /><br/>
<sub><b>Transport Coordination</b></sub>
</td>
</tr>
</table>

### Mobile

<p align="center">
  <img src="screenshots/Screenshot%202026-09-07%20231838.png" width="200" alt="Selling journey on mobile" />
  &nbsp;&nbsp;
  <img src="screenshots/Screenshot%202026-09-07%20231904.png" width="200" alt="Farmer dashboard on mobile" />
</p>
<p align="center"><sub><b>Selling Journey</b> &nbsp;·&nbsp; <b>Mobile Dashboard</b></sub></p>

More screenshots are available in [`screenshots/`](screenshots/), including
the registration screen and a couple of in-progress development captures
kept for historical/audit purposes.

## Installation

### Prerequisites
- Python 3.11+, Node.js 18+, a PostgreSQL database (Supabase works well for
  a free hosted instance).

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL and SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env   # point VITE_API_URL at your backend
npm run dev
```

## Environment Variables

See `backend/.env.example` and `frontend/.env.example` for the full list.
At minimum, the backend needs `DATABASE_URL` (PostgreSQL) and `SECRET_KEY`
(JWT signing); no real secrets are committed to this repository.

## Running Locally

1. Start the backend (`uvicorn`, above) — it creates its own tables on
   first run against an empty database.
2. Start the frontend (`npm run dev`).
3. Register a farmer and a buyer account, or use any demo accounts your
   deployment has seeded, and walk the flow described in
   [How CropWise Works](#how-cropwise-works).

## Deployment

The reference deployment (referenced in in-app copy and screenshots) runs
the frontend on Vercel and the backend on a Postgres/Supabase-backed host;
no deployment configuration files specific to a provider were found in this
repository snapshot, so deployment steps are environment-dependent rather
than one-command.


---

