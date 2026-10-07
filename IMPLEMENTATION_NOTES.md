# Multi-round crop-deal negotiation: implementation notes

Buyer and farmer can now negotiate a crop offer over any number of rounds
(counter / accept / reject / withdraw) with immutable per-round history. The
accepted round becomes the authoritative deal price. All acceptance (legacy and
new) goes through one shared finalization routine.

## What was implemented
- **One immutable row per round** (`buyer_offer_rounds`). `BuyerOffer.status` stays the thread-level state (`pending` = negotiation open; `accepted` / `rejected` / `withdrawn` are terminal).
- **Strict turn-taking.** Only the receiver of the latest `PENDING` round may accept, reject or counter. Only its sender may withdraw.
- **Identity from authentication.** Sender, receiver and farmer are derived from the JWT plus listing/lot ownership. Request bodies contain no ids (a test sends fake ids and checks they are ignored).
- **Shared finalization** (`services/offer_negotiation.py::finalize_acceptance`). It re-locks and re-validates the listing/lot (no oversell), decrements inventory, closes sibling threads on sell-out, snapshots the agreed terms, creates the `Transaction` (farmer_id from *ownership*, so a buyer-initiated accept is recorded correctly) and writes the timeline events.
- **Legacy endpoints preserved** (`POST /offers`, the list endpoints, `PATCH /offers/{id}/accept|reject`). Never-countered offers behave exactly as before: same messages, 403s and transaction output (same 2 events), verified by the original suite plus characterization tests. The legacy PATCH endpoints are now turn-aware, so a farmer cannot accept their own counter.
- **Backfill.** Idempotent startup backfill (round 1 for each existing offer) plus lazy backfill on first use, so directly inserted or legacy offers are always negotiable.
- **Notifications** use the existing helpers: `offer_countered`, `offer_accepted`, `offer_rejected`, `offer_withdrawn` go to the counterparty (sent after commit).
- **Frontend:** API methods, a reusable negotiation thread component (history, loading/error/empty states, accept/reject/counter/withdraw with confirmation, 409 stale handling), wired into Marketplace (farmer, per listing), Lots (farmer, per lot) and Buyer Dashboard (buyer). The timeline shows the new `OFFER_COUNTERED` events.
- **Translations:** 48 new keys in all 15 locale files (see assumptions).
- `transport_negotiation.py` and the transport flow are **untouched** (verified: empty git diff; all transport tests pass).

## Files
**Added**
- `backend/app/services/offer_negotiation.py`: shared logic
- `backend/app/routers/offer_negotiation.py`: new endpoints
- `backend/tests/test_offer_negotiation.py`: 24 tests
- `backend/tests/test_offer_negotiation_contract.py`: frontend API calls vs backend routes
- `frontend/src/components/OfferNegotiation.jsx`
- `IMPLEMENTATION_NOTES.md`

**Modified**
- `backend/app/models.py`: `BuyerOfferRound` model; new `BuyerOffer` columns and relationship
- `backend/app/schemas.py`: `OfferOut` gains optional fields; `OfferCounter`, `OfferRoundOut`, `OfferThreadOut`
- `backend/app/auth_utils.py`: `require_farmer_or_buyer`
- `backend/app/routers/offers.py`: writes round 1 on create; list endpoints annotated; legacy accept/reject refactored onto the shared service
- `backend/app/database.py`: additive column migrations (SQLite and Postgres paths)
- `backend/app/main.py`: router include and startup backfill
- `frontend/src/api/client.js`: 7 new methods; errors now carry `.status`
- `frontend/src/pages/Marketplace.jsx`, `Lots.jsx`, `BuyerDashboard.jsx`
- `frontend/src/i18n/translations/*.json` (15 files)

## Database / migration
- New table `buyer_offer_rounds` (created by `create_all`). Columns: offer_id, sequence, sender_role/id, receiver_role/id, price_per_kg, quantity_kg, message, language, status, created_at, responded_at. `UNIQUE(offer_id, sequence)`.
- New nullable columns on `buyer_offers`: `updated_at`, `accepted_round_id`, `agreed_price_per_kg`, `agreed_quantity_kg`, `agreed_at`. Added by `run_lightweight_migrations()` (`ADD COLUMN IF NOT EXISTS` on Postgres; PRAGMA-guarded on SQLite). Additive only; nothing is dropped or rewritten.
- Backfill maps pending→PENDING, accepted→ACCEPTED, rejected→REJECTED, withdrawn→WITHDRAWN. Offers whose listing/lot no longer exists are skipped. It was verified against a database created with the previous schema.
- `offered_price_per_kg` / `quantity_kg` **mirror the latest round** while the thread is open; all earlier values stay in the rounds table.

## API
New (all require a farmer or buyer JWT; non-participants get 404):

| Method and path | Who | Notes |
|---|---|---|
| `GET /offers/awaiting-me` | either | open threads where it is my turn |
| `GET /offers/{id}` | participant | thread: offer, rounds, `can_act`, `awaiting_role`, public profiles, target summary, `transaction_id`. The farmer's minimum price is shown to the farmer only. |
| `GET /offers/{id}/rounds` | participant | full history |
| `POST /offers/{id}/counter` | receiver of the current round | body: `price_per_kg`, optional `quantity_kg`, `message`, `language`, `based_on_round_id` |
| `POST /offers/{id}/rounds/{rid}/accept` | receiver | same response shape as legacy plus extras |
| `POST /offers/{id}/rounds/{rid}/reject` | receiver | closes this buyer's thread only |
| `POST /offers/{id}/withdraw` | sender of the current round | thread becomes `withdrawn` |

Changed: `POST /offers` also writes round 1. The list endpoints and `/offers/mine` now include `awaiting_role` and `round_count`. `PATCH /offers/{id}/accept|reject` are unchanged in path and messages but return 400 when it is the buyer's turn.

Status codes: 404 non-participant / missing; 403 wrong role (new endpoints) and legacy ownership; 400 out of turn, terminal thread, validation, round cap (20); **409** stale round, a mismatched `based_on_round_id`, or a lost concurrent-insert race.

## Run
```bash
# backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set DATABASE_URL (PostgreSQL/Supabase)
uvicorn app.main:app --reload
# frontend
cd frontend && npm install && npm run dev
# tests
cd backend && python -m pytest tests -q          # 223 passed, 6 skipped
cd frontend && npm run build                     # builds cleanly
```

## Assumptions (the open decisions in the analysis)
1. Mirror fields to the latest round: yes.
2. Quantity is negotiable (it must stay within what is available).
3. The minimum-price floor is enforced on **buyer** rounds only. A farmer may counter below their own minimum. The new counter error does not reveal the floor value (legacy create still does).
4. No new one-open-thread-per-buyer rule (the existing duplicate-offer behaviour is unchanged).
5. The transaction timeline is rebuilt from the rounds (original timestamps, new `OFFER_COUNTERED` events). Never-countered offers produce the same two events as before.
6. New endpoints use POST; non-participants get 404; legacy PATCH endpoints keep their 403s.
7. Round cap 20; no expiry.
8. Transactions still start at `OFFER_ACCEPTED`, even when the buyer accepts.

## Limitations
- **Locking is untested on real PostgreSQL.** `SELECT … FOR UPDATE` is a no-op on SQLite (the test DB). The `UNIQUE(offer_id, sequence)` constraint is the backstop and is tested by simulating the conflict.
- **No browser-level UI test.** There is no frontend test runner in the repo. The frontend was verified by a clean `vite build`, a check that every translation key used exists, and a pytest contract test of client.js against the backend routes.
- **Translations:** hi / bn / mr were translated by me and should get a native-speaker review. The other 10 locales contain English text for the new keys, matching how they already stand. `npm run i18n:validate` was already failing before this change and still reports the same kinds of issues.
- Bidirectional notifications on offer *creation* were not added (the legacy flow had none).
- Known pre-existing issues were deliberately not changed: `bidding_deadline` is not enforced; a partial lot accept resets the lot to AVAILABLE even if other offers are pending; a buyer demand is marked FULFILLED on a partial lot accept.
- The product still says "CropWise" in code and UI strings (not part of this task).
