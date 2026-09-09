# CropWise MVP Status — Audit of `CropWise_GPS_CHECKPOINT.zip`

Legend: ✅ complete/working · ⚠️ partial · ❌ missing/broken · 🚫 not implemented, not invented

This is an evidence-based audit (code inspection + actual test run), not a
description of intent. Every line below was verified against this specific
checkpoint just now — I did not assume anything carried over from earlier
turns, because it demonstrably hasn't (see items 1 and 2, which regressed
across at least three checkpoints in this conversation).

## 1. Data-correctness regressions (highest priority — carried over from
   two turns ago, confirmed STILL present in this checkpoint)

| Status | Feature | Evidence | What's missing | Action |
|---|---|---|---|---|
| ❌ | Live market-data record validation | `live_market_data.py`: `filters[state]` (not `state.keyword`), `latest = records[0]` with zero cross-check against requested market/commodity | The Kharsiya-mislabeling bug is back — a returned record for a *different* market could be shown under the requested market's name | Restore `state.keyword` filter + strict per-field match validation before accepting any record |
| ❌ | FarmPool honesty labels | `transport_optimizer.py`'s `find_nearby_pool_partners()`/`shared_transport_plan()` have no `is_simulated`/disclaimer field; `FarmPool.jsx` has zero mention of "simulated" | Fabricated farmer names ("Anita Patel" etc.) shown with no disclaimer, indistinguishable from real people | Add `pool_partners_are_simulated` + disclaimer, wire into `FarmPool.jsx` |

## 2. Genuinely more advanced than I expected (verified, not assumed)

| Status | Feature | Evidence |
|---|---|---|
| ✅ | Transport realism | `transport_optimizer.py` has a real vehicle-class/diesel/driver/overhead/toll/minimum-trip model (an independently-written equivalent of the Priority-2 fix from earlier in this conversation — different code, same intent, genuinely realistic) |
| ✅ | AI Assistant intent routing | `assistant.py` has real, distinct handlers for `MARKET_RECOMMENDATION`, `PRICE_LOOKUP`, `PRICE_FORECAST`, `PROFIT_CALCULATION`, `BUYER_SEARCH`, `WEATHER`, `NEEDS_CLARIFICATION` — `PRICE_FORECAST` genuinely calls `forecast.get_forecast`, `BUYER_SEARCH` genuinely queries real `BuyerDemand` rows, not a market-comparison fallback |
| ✅ | GPS state machine | `utils/location.js` implements all 7 states (`IDLE/DETECTING/SUCCESS/PERMISSION_DENIED/TIMEOUT/UNAVAILABLE/UNSUPPORTED`) as a reusable hook, correctly mapped from the browser's `GeolocationPositionError` codes, and is actually wired into 7 pages (`MarketIntelligence`, `BestOption`, `PriceForecast`, `AIAdvisor`, `ArrivalIntelligence`, `FarmPool`, `Auth`) |
| ✅ | Weather | `weather_service.py` + `weather.py` router present and consistent with the LIVE/DEMO/UNAVAILABLE design from earlier in this conversation |
| ✅ | i18n coverage on key pages | `FarmerDashboard.jsx` (59 `t()` calls) and `SellingJourney.jsx` (25 `t()` calls) are genuinely translated, not just scaffolded — 10 locale files present (`en, mr, ta, pa, gu, ml, kn, ur, bn, bho`) |
| ✅ | Quality grading honesty | Explicitly self-documented as a heuristic pixel-statistics analyzer, `demo_mode`-labeled throughout, not claiming to be a trained CV model |
| ✅ | Price forecasting honesty | Documented as a transparent trend+volatility regression, not a black-box/ML claim, with a genuine walk-forward backtest function |
| ✅ | Admin RBAC | `require_admin` dependency actually gates admin endpoints (`impact_dashboard`, `user_activity`) |
| ✅ | Buyer matching | Real explainable 0–100 score (price attractiveness, reliability, payment history) — not a placeholder |

## 3. Confirmed real but architecturally limited (be honest, not dismissive)

| Status | Feature | Evidence | Note |
|---|---|---|---|
| ⚠️ | Payments | `models.Payment` exists, tracks state transitions | No real payment gateway (no Razorpay/Stripe integration found) — this is simulated transaction-state tracking, not a live financial system. Should be labeled as such in any UI that shows it, per the mega-prompt's own instruction not to "pretend it is a real payment gateway" |
| ⚠️ | Storage / FarmPool backends | Real models (`StorageFacility`, `StorageBooking`) and a real `/group-selling` router with `/join` — not fully traced end-to-end (booking → cost → completion) in this pass given time constraints | Needs a deeper trace before calling it ✅ |

## 4. Test results (actually run just now, not assumed)

```
65 passed, 5 errors, 7 warnings
```
The 5 errors are the same pre-existing, unrelated `test_login_tracking.py` failure from earlier in this conversation (`passlib`/`bcrypt` version incompatibility — `bcrypt` 4.x removed an attribute `passlib` 1.7.4 expects). Not caused by anything in this checkpoint or this audit.

## 5. Not audited this pass (time-boxed, being honest about it)

Marketplace end-to-end listing visibility, Transactions ownership/RBAC edge cases, Notifications delivery, full i18n audit beyond the two files sampled, and all responsive/browser testing (same Chromium-install blocker as every prior attempt in this conversation — still genuinely unavailable in this sandbox).

---

**Per this prompt's own instruction, I'm stopping here rather than beginning to code** — this audit is real, not a rubber stamp, and the two regressions in §1 are concrete and quick to fix. Given the size of the remaining mega-prompt (dashboard redesign, full i18n audit, deeper marketplace/transaction tracing), tell me what to prioritize next.
