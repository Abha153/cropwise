# CropWise — Session Handoff

## Session update — 2026-09-17, this session (Transporter role backend)

**Environment note (unchanged from prior session):** this sandbox has no
outbound network access. `pip install -r requirements.txt` fails (no
package index reachable), so **the backend test suite was NOT executed
this session** — only `python -m py_compile` (syntax-only) on every
new/changed file, which passed. The new tests below have been reviewed
line-by-line for logical correctness but their actual pass/fail status is
**NOT VERIFIED**. Run them yourself (section 5) before trusting this.

**Implemented this session: real authenticated Farmer <-> Transporter
role, negotiation, chat, status, reviews (doc items 1-8 below, previously
flagged as the single largest gap in this handoff).**

- `app/models.py`: new `Transporter`, `TransportOffer` (persistent
  multi-round offer history, sequence-numbered, never overwritten),
  `TransportMessage` (chat), `TransportReview` (two-sided, separate from
  the FarmPool-scoped `TripReview`). New columns on the existing
  `TransportRequest` (`transporter_id`, `negotiation_status`,
  `claimed_at`, `transporter_agreed_price`, `completed_at`) -- fully
  additive; the legacy farmer-recorded `quote_status`/`quoted_price`/
  `agreed_price` fields are untouched and still work (see regression
  test).
- `app/database.py`: additive migrations for both SQLite and Postgres
  paths, same pattern as every existing migration in this file.
- `app/auth_utils.py`, `app/routers/auth.py`: `transporter` added as a
  third JWT role. `/auth/register/transporter`, transporter branch in
  `/auth/login`, `require_transporter`, `require_farmer_or_transporter`.
- `app/routers/transporters.py` (new): dashboard -- available (unclaimed)
  requests with farmer PII withheld until claimed, race-safe claiming,
  assigned requests, profile.
- `app/routers/transport_negotiation.py` (new): turn-enforced multi-round
  offers (first offer must be the transporter's; each side must wait for
  the other to respond; accept/reject only by the offer's receiver;
  server-derived pricing, never client-supplied), chat, transporter-driven
  status transitions (PICKED_UP/IN_TRANSIT/DELIVERED/COMPLETED), two-sided
  reviews with rating aggregation onto `Transporter.rating` and
  `Farmer.rating`.
- `backend/tests/test_transporter_workflow.py` (new, ~30 tests): RBAC,
  claiming, the exact negotiation example from spec (1350->1275 accept),
  out-of-turn/stale-offer/duplicate-accept/unauthorized-access rejection,
  chat authorization, status-transition validation, review rules
  (pre-completion rejection, duplicate rejection, unrelated-user
  rejection), and a regression test proving the legacy farmer-only quote
  flow is unaffected.

**NOT done this session (still open, being tracked honestly rather than
silently dropped):**
- Frontend: no transporter login/register page, no transporter dashboard,
  no negotiation/chat UI. `AuthContext.jsx`/`ProtectedRoute.jsx` are
  already role-string-agnostic (no farmer/buyer hardcoding), so wiring in
  a third role is mechanical but not yet done.
- i18n: none of the new backend-only work has user-facing strings yet
  (no frontend exists for it), so there is nothing to translate. A full
  i18n audit across all 15 locale files for the *existing* product was
  requested but not performed this session -- out of scope for the time
  available.
- Market-data provenance reclassification (LIVE vs SOURCE SNAPSHOT vs
  DEMO vs UNAVAILABLE), Maharashtra real-mandi-data import, payment/
  receipt claim audit, FarmPool shared-cost recalculation from agreed
  (not estimated) price, and full end-to-end journey verification were
  all requested in the same pass and were **not attempted** this session
  -- there was not enough remaining capacity to do them honestly (i.e.
  actually verified, not just described) alongside the transporter
  backend work above. Flagging this explicitly rather than claiming
  partial or fabricated coverage.



**Environment note (important):** this sandbox has no outbound network
access (`pip install` and `npm install` both fail — no package index
reachable). This means **neither the backend test suite nor the frontend
build could be executed or verified this session.** Every claim below is
based on reading the actual backend response shapes and existing frontend
conventions, not on a passing test run. Run the commands in section 5
yourself before trusting this is bug-free.

**Implemented: Receipt UI (doc item 9)** — the backend for this
(`Receipt` model, `receipt_service.py`, `/receipts/*` router) already
existed and was already working per the previous session's notes; only the
UI was missing, exactly as flagged below ("Frontend UI for receipts...:
the APIs and client methods exist, but no component renders them yet").
- `frontend/src/pages/TransactionDetail.jsx`: new `ReceiptPanel`
  component, added as a new card in the existing two-column layout
  (next to Payment, same card styling/classes as everything else on the
  page — no layout/sidebar/nav changes). Shown only when the transaction
  status is one of `COMPLETED` / `PAYMENT_RECEIVED` / `DELIVERED`
  (matching the backend's own `RECEIPTABLE_STATUSES`).
  - "Generate Receipt" → `POST /receipts/transaction/{id}` (idempotent
    server-side, so a second click just returns the same receipt — no
    special handling needed client-side).
  - Displays receipt ID, generated timestamp (via the shared `fmt()` /
    Indian-format datetime util, not a browser-local string), and the
    SHA-256 hash value returned by the backend.
  - "Download Receipt" → fetches the real `GET /receipts/{id}/download`
    plain-text document (not JSON) and saves it client-side as a `.txt`
    file via a Blob + temporary `<a download>`, since the existing
    `request()` helper in `api/client.js` always calls `res.json()`.
    Added a dedicated `api.downloadReceipt()` that fetches raw text
    instead.
  - "Verify Integrity" → `GET /receipts/{id}/verify`. Renders
    ✅/❌ from the backend's own `integrity_verified` boolean — **the
    frontend does not compute or compare any hash itself.**
  - Renders the backend's `note` field (the "SHA-256 proves content
    integrity, not that the transaction occurred" caveat) verbatim
    rather than writing new wording for it.
- `frontend/src/api/client.js`: added `downloadReceipt()`.
- `frontend/src/i18n/translations/en.json`: added the ~12 new
  `transactionDetail.receipt*` keys this panel uses. Not added to the
  other 14 locale files — same pre-existing fallback pattern the repo
  already relies on for `transport.*` (`dict[key] || enDict[key] ||
  key`), so nothing breaks, English shows through on other locales for
  just these new strings.
- **Caught while writing this:** the backend's `verify_receipt()` returns
  `integrity_verified` (plus `result: "INTEGRITY_VERIFIED" |
  "INTEGRITY_MISMATCH"`), not `valid` — checked the actual service code
  before wiring the button rather than guessing the field name.

**NOT done this session (still outstanding, unchanged from before):**
- The entire transporter workflow (doc items 1–8: transporter role/
  account/RBAC, farmer↔transporter messaging, multi-round negotiation as
  a true second actor, status lifecycle, two-sided reviews). This is
  large — a transporter actor, auth, and RBAC from scratch, a message
  model, a negotiation state machine, and a second review direction — and
  was not attempted this session. See "Priority 4–7" below for what
  exists today as a *partial* substitute (farmer-owned quote fields, not
  a real transporter account).
- Market data freshness UI (doc item 10): **already implemented**, not
  new this session — `MarketIntelligence.jsx` already shows
  observed/fetched timestamps and a live-vs-demo source badge per row
  (🟢 Government Mandi Price / 🟣 District Reference Price / 🟡 Demo
  Data) plus a page-level live/demo notice. It does not use the literal
  words "Status: LIVE" / "Status: FALLBACK" from the spec, or surface
  `last_successful_sync` specifically — if that literal wording/field is
  required, treat it as a follow-up, not as done.
- Mandi sync hardening (item 11), AgriAdvisor intent upgrade (items
  13/14), "Ask AgriAdvisor" + decision provenance (items 15/16): not
  touched.
- No tests were added for the Receipt UI this session (no frontend test
  runner is configured in this repo at all — confirmed in the prior
  session's notes — and the backend receipt tests already existed
  unchanged).

---

Backup created: 2026-09-16 11:46 UTC
Git: no `.git` directory is present in this archive, so no branch/commit hash is
available. This is a plain source snapshot, not a git checkout.

## 1. Current implementation status

This backup contains three features implemented and tested in this session, on
top of what was already in `CropWise_Latest__1_.zip`:

### A. Transport quote / negotiation (DONE, tested)
- `TransportRequest` gained: `quote_status`, `quoted_price`/`quoted_at`,
  `counter_price`/`counter_by`/`counter_at`, `agreed_price`/`agreed_at`,
  `picked_up_at`, `delivered_at`.
- New endpoints on `/transport`: submit quote, one counter-offer round,
  accept, reject — all farmer-ownership-checked, agreed price computed
  server-side only.
- **Important scoping decision:** there is no transporter login/account
  system anywhere in this codebase (only farmer/buyer/admin roles). The
  quote is recorded by the farmer who owns the request (the same way
  `driver_name`/`driver_contact` already are), not by an authenticated
  transporter. This is documented in `models.py` next to the new columns.
- Frontend: new `frontend/src/components/TransportQuoteSection.jsx`, wired
  into `Transport.jsx`. Estimate → quote → agreed price hierarchy.
- Tests: `backend/tests/test_transport_quote.py` (12 tests).

### B. Timestamp surfacing (DONE for transport/payment; partial elsewhere)
- `picked_up_at`/`delivered_at` are real server timestamps, set only on the
  actual status transition (not inferred from `updated_at`).
- `TransactionDetail.jsx`'s duplicate local `fmt()` was removed in favour of
  the shared `frontend/src/utils/datetime.js` formatter (already existed
  before this session; this session only consolidated the one remaining
  duplicate).
- Payment timestamps (`initiated_at`/`received_at`) already existed and
  were already displayed correctly before this session — confirmed, not
  rebuilt.
- Receipt timestamp: **not implemented** — there is no receipt concept
  anywhere in the backend (confirmed by search). Do not add a receipt
  timestamp without first building an actual receipt entity.
- Market data `fetched_at`/`observed` timestamps: already implemented
  before this session (verified present in `compare_markets()` and
  `MarketIntelligence.jsx`); not touched this session.
- **Not done:** doc 12's full sweep of every other page (marketplace,
  notifications, etc.) — only transport + the one payment-formatter
  consolidation were addressed this session.

### C. Buyer verification workflow (DONE, tested)
- Reused the existing `BuyerVerification` model/router (5 internal states:
  PENDING/UNDER_REVIEW/VERIFIED/REJECTED/SUSPENDED) rather than rebuilding
  it. Added a single mapping layer,
  `app/routers/buyer_verification.py::display_info()`, that maps those to
  the 4 required canonical tiers:
  - `PENDING` (no row) → `INSUFFICIENT_VERIFICATION_EVIDENCE`
  - `UNDER_REVIEW` → `SELF_DECLARED`
  - `VERIFIED` → `PLATFORM_VERIFIED`
  - `REJECTED` / `SUSPENDED` → `VERIFICATION_REJECTED`
- Added `submitted_at`, `reviewed_at`, `reviewed_by` to `BuyerVerification`,
  and a new `BuyerVerificationAuditLog` table (buyer id, old status, new
  status, reviewer, note, timestamp) — there was no audit trail before this.
- New public `GET /buyer-verification/{buyer_id}/badge` — never 404s;
  defaults to `INSUFFICIENT_VERIFICATION_EVIDENCE` for a buyer with no
  submission.
- Frontend: new `frontend/src/components/VerificationBadge.jsx`, replacing
  the old generic "✓ Verified Buyer" checkmark in `Lots.jsx` and
  `BuyerDemands.jsx` with the real 4-tier badge + tooltip.
- AgriAdvisor's `BUYER_SEARCH` answer in `assistant.py` now appends each
  buyer's real display label (e.g. `[Platform Verified]`) — pulled from the
  same mapping function, never invented.
- Tests: `backend/tests/test_buyer_verification.py` (9 tests). One of these
  tests caught a real bug (a key-naming mismatch that silently dropped the
  display fields from API responses) before it shipped — fixed, verified.

### D. Everything else in this repo
Unchanged from `CropWise_Latest__1_.zip` (which itself already contained a
large, mature feature set — 26 backend routers, 20+ DB models, TripReview,
multi-source market data, etc.). See the top-level `README.md` for the full
picture; it has not been edited this session except as noted above.

## 2. NOT implemented this session (started, then paused for this backup)

**Doc 10 — official mandi-data sync (`sync_official_mandi_prices()`):**
audited only. Confirmed the building block this needs already exists
(`app/services/live_market_data.py::fetch_live_price_status()`, which
already returns the exact fields requested: crop/market/state/arrival_date/
min/max/modal price/variety/grade/source/provider/fetched_at), and that
Maharashtra already has 10 markets defined in
`app/mock_data/locations.py`. **No new code was written for this yet** —
no `sync_official_mandi_prices()` function, no `/market/sync-official`
endpoint, no upsert/dedup logic, no `last_successful_sync` field, no tests.

Also confirmed directly (this session, via `curl -i` with headers) that
`api.data.gov.in` is blocked from this sandbox:
`HTTP/2 403`, `x-deny-reason: host_not_allowed`. Any live-ingestion claim
must account for this — building the sync architecture is possible without
network access (and should be tested with a mocked HTTP layer), but an
actual successful live fetch cannot be demonstrated from this environment.

**Doc 12 — full timestamp sweep:** only the transport + payment-formatter
pieces above were done. Marketplace, notifications, and receipt-adjacent UI
were not audited this session.

## 3. Known issues (pre-existing, not introduced this session)

- `TransactionDetail.jsx`'s buyer-facing "Pay Now" button still calls
  Razorpay order-creation/verify endpoints (`/payments/create-order`,
  `/payments/{id}/verify`) that **do not exist in the backend**. The
  backend's real payment flow is the simulated PENDING→INITIATED→PAID
  tracker via `/payments/{id}/initiate` and `/payments/{id}/confirm-received`.
  This was flagged in the project's own README before this session; not
  fixed here (out of scope for the sessions that produced this backup).
- i18n: the new quote/verification strings added this session have real
  translations only in `en`/`hi`/`mr`. The other 12 locales — and, it turns
  out, the *entire pre-existing* `transport.*` namespace — have no
  non-English translations at all; this is a pre-existing gap (confirmed
  by inspection), not a regression. The app's fallback
  (`dict[key] || enDict[key] || key`) means nothing breaks, text just
  displays in English on those pages for those languages.
- No Alembic/migration framework exists. Schema changes rely on
  `run_lightweight_migrations()` in `backend/app/database.py`
  (`ADD COLUMN IF NOT EXISTS` for Postgres, a small helper for SQLite).
  Every new column added this session has an entry there — check that file
  first if a future column doesn't seem to appear on a live DB.

## 4. Test / build status (this backup, verified by actually running them)

```
Backend:  143 passed, 6 skipped, 0 failed   (pytest, SQLite in-memory DB)
Frontend: npm run build succeeds (~934 kB main bundle, 239 kB gzipped;
          pre-existing >500kB chunk-size warning, not a new error)
Frontend automated tests: none configured in this repo (no test script in
          package.json) — nothing to run.
```

## 5. Exact commands to run the project

Backend:
```
cd backend
pip install -r requirements.txt
# DATABASE_URL must point at a real Postgres/Supabase instance for the app
# itself (not sqlite:///:memory: — that's test-only). Copy .env.example to
# .env and fill in real values first; .env is intentionally NOT in this ZIP.
uvicorn app.main:app --reload --port 8000
```

Frontend:
```
cd frontend
npm install
npm run dev        # dev server
npm run build       # production build -> frontend/dist
```

Backend tests:
```
cd backend
DATABASE_URL="sqlite:///:memory:" SECRET_KEY="test-secret-key" python -m pytest -q
```

---

## Session update — Receipts, SHA-256 integrity, payment-flow repair

### Implemented

**Priority 8/9 — Receipt generation + SHA-256 integrity** (new)
- `backend/app/models.py` → `Receipt` model (`receipt_id`, `transaction_id`,
  `receipt_version`, `payload` JSON snapshot, `hash_algorithm`, `hash_value`,
  `generated_at`).
- `backend/app/services/receipt_service.py` → canonical JSON serialisation
  (sorted keys, no insignificant whitespace) → SHA-256; generation,
  verification, and a plain-text downloadable document.
- `backend/app/routers/receipts.py` → `POST /receipts/transaction/{id}`,
  `GET /receipts/transaction/{id}`, `GET /receipts/{receipt_id}/download`,
  `GET /receipts/{receipt_id}/verify`. Access limited to the transaction's
  farmer, its buyer, or an admin.
- Receipts are idempotent per transaction (re-requesting returns the same
  issued document, not a new hash) and only issued once a transaction
  reaches COMPLETED / PAYMENT_RECEIVED / DELIVERED.
- Generating a receipt writes a `RECEIPT_GENERATED` TransactionEvent.

**IMPORTANT WORDING — do not overstate this.** The SHA-256 hash proves the
receipt's stored content has not been altered since it was generated. It
does NOT prove the underlying real-world transaction occurred. That caveat
is in `receipt_service.INTEGRITY_NOTE`, returned by the API, printed on the
downloadable document, and asserted by a test. Keep it that way.

**Priority 3 — Payment flow repaired**
The frontend was calling four Razorpay endpoints that do not exist in this
backend (`/payments/create-order`, `/payments/{id}/verify`, `/cancel`,
`/failed`) — clicking "Pay Now" would have failed against a live backend.
Option B (real Razorpay) was not available: no `razorpay` package in
requirements, no `RAZORPAY_KEY_ID`/`SECRET` in config or `.env.example`.
Took Option A: removed the dead calls and the Checkout script loader, and
wired the button to the real, already-working lifecycle
(`createPayment` → `initiatePayment` → farmer `confirm-received`).
Button relabelled "Mark payment initiated" — it records status, it does not
move money. All timestamps remain server-generated.

### Verified this session
- Backend: 161 passed, 6 skipped (was 152/6).
- Frontend: production build PASS; zero `razorpay` references remain.
- Phase 2 buyer verification re-verified empirically (new buyer with no
  row → INSUFFICIENT_VERIFICATION_EVIDENCE; PENDING/UNDER_REVIEW/VERIFIED/
  REJECTED map to the four specified display statuses).
- Priority 1 (market validation regression) and Priority 2 (FarmPool
  honesty) were already implemented and passing — not rebuilt.

### NOT done this session (genuinely outstanding)
- Priority 4 — transporter role/account (no transporter login exists).
- Priority 5 — farmer↔transporter messaging.
- Priority 6 — multi-round negotiation (current impl is single farmer-side
  counter, farmer-owned; needs the transporter actor from P4 first).
- Priority 7 — transporter→farmer review direction.
- Priority 13/14 — TF-IDF / semantic intent layer, LLM explanation layer.
- Priority 15/16 — "Ask AgriAdvisor" contextual action, decision provenance UI.
- Frontend UI for receipts and for market freshness badges: the APIs and
  client methods exist, but no component renders them yet. Do not claim
  these as complete on the strength of the backend alone.

### Blocked by environment
`api.data.gov.in` and CEDA are outside this sandbox's network allowlist.
Mandi sync logic is tested against mocked provider responses only.
**A real successful live fetch has never been observed.** Do not mark
"live ingestion verified" until someone runs
`POST /market/sync?state=Maharashtra` with a real key and sees records land.

---

## Session update — Transporter frontend wired, route + i18n completed

### Implemented and verified this session
- `/transporter/dashboard` route wired into App.jsx with `Protected role="transporter"`
  — reuses the existing ProtectedRoute mechanism unchanged, so farmer/buyer/admin
  are redirected away exactly like every other role-gated route already works.
- `TransporterDashboard.jsx` completed: available/my requests, offer history,
  make/accept offer, chat panel, status advancement (CONFIRMED/MATCHED->PICKED_UP
  ->IN_TRANSIT->DELIVERED->COMPLETED), and a review form gated on DELIVERED/COMPLETED.
  All data comes from the real backend APIs added to api/client.js this session --
  no mock/hardcoded transport requests.
- 29 `transporter.*` i18n keys added to en.json (dashboard, offers, chat, review
  strings) -- every new string in TransporterDashboard.jsx and the Auth.jsx
  transporter registration fields uses t(), none hardcoded.
- Backend: 191 passed, 6 skipped, 0 failed (unchanged from the relationship fix
  earlier this session -- no backend regressions from the frontend work).
- Frontend: `npm run build` passes clean.

### Verified role protection (via ProtectedRoute's existing mechanism, not new code)
`Protected role="transporter"` on `/transporter/dashboard` means any role other
than "transporter" is redirected to "/" on that route -- the same mechanism
already protecting `/farmer/dashboard` (role="farmer") and `/buyer/dashboard`
(role="buyer"). Not separately re-implemented; inherited for free.

### NOT done this session (genuinely outstanding -- do not claim otherwise)
- **i18n is INCOMPLETE, not audited.** Only en.json got the new transporter
  keys. Hindi/Marathi/other locales were NOT touched -- they fall back to
  English for every new key via the existing fallback mechanism (see
  I18nContext.jsx), which is honest behavior but is NOT translation. No
  whole-product key-parity audit was run this session.
- **FarmPool shared-cost integration not started.** Farmer's FarmPool share is
  still calculated from `estimated_cost`, not `transporter_agreed_price`, once
  a real negotiated agreement exists. This is a real, not-yet-closed gap.
- **Farmer-side Transport.jsx not updated** to show the real transporter
  identity/negotiation history/chat once a transporter claims a legacy-style
  request -- the existing TransportQuoteSection.jsx (farmer-recorded quote)
  still runs alongside the new transporter flow without a unified farmer view.
- **No end-to-end manual verification was performed** (no browser in this
  environment) -- each backend endpoint is unit/integration tested, and the
  frontend calls the documented real routes, but no one has clicked through
  farmer->transporter->delivery->review in a running app.
- **Maharashtra market-data provenance audit not performed this session.**
- Payment/receipt audit: unchanged from the prior session's work (Priority 3/8/9
  already done and documented above); not re-audited this pass.

### Blocked by environment (unchanged)
`api.data.gov.in`/CEDA unreachable from this sandbox -- mandi sync still only
verified against mocked provider responses.
