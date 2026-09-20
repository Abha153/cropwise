# Session checkpoint — new work only (not the full baseline)

Baseline: uploaded CropWise_transporter_frontend_20260917.zip (CropWise_Final/)

## 1. FarmPool agreed-price integration (DONE, partially verified)
- backend/app/schemas.py — added `transport_request_id` to FarmPoolRequest
- backend/app/routers/logistics.py — /logistics/farmpool now looks up the
  real TransportRequest and, only if transporter_agreed_price is set
  server-side, uses it as the allocation basis (never client-supplied).
- backend/app/services/transport_optimizer.py — shared_transport_plan()
  takes optional agreed_transport_price; existing proportional allocation
  rule is applied to it; the estimate is preserved alongside
  (`estimated_shared_transport_cost` / `your_estimated_shared_share`);
  `cost_basis`/`label` = "AGREED" | "ESTIMATED".
- frontend/src/pages/FarmPool.jsx — lets farmer link one of their own
  agreed transport requests (api.myTransportRequests(), filtered to
  transporter_agreed_price != null); shows honest AGREED vs ESTIMATED
  banner.
- backend/tests/test_farmpool_agreed_price.py — new tests incl. the
  estimated=1700/agreed=1500 scenario.

  VERIFICATION STATUS: pytest/fastapi/sqlalchemy are not installed in
  this sandbox and it has no network access, so the endpoint-level
  (TestClient/DB) tests could not be executed. The pure-logic tests
  (no fastapi/sqlalchemy import needed) WERE run manually with `python3`
  and passed. This is a real, disclosed limitation, not a claimed PASS.

## 2. i18n audit (real numbers gathered; fixes NOT yet applied)
- i18n_audit/i18n_audit.py — script comparing all 15 locale JSON files
  against English (1177 keys).
- i18n_audit/i18n_report.json — its output.
- i18n_audit/find_hardcoded.py — heuristic scan for hardcoded JSX text
  not wrapped in t().

  FINDINGS (real, not estimated):
  - en: 1177 keys (baseline)
  - hi: 505 keys present, 678 missing (~58%)
  - mr: 305 keys present, 878 missing (~75%)
  - bn/ta/te/gu/kn/ml/pa/or/as/ur/bho/mai: 186 keys each, ~997 missing
    (~85%) -- ENTIRE feature areas (auth, transport, marketplace, lots,
    admin, payments, verification, storage, etc.) are 100% missing and
    silently fall back to English for these 12 locales.
  - No MutationObserver/legacy glossary masking mechanism found in the
    codebase (checked, not present).
  - Hardcoded English JSX text found: concentrated in
    frontend/src/pages/AIAdvisor.jsx (~59 instances -- appears to be a
    newer hardcoded rewrite sitting above a dead, already-t()-ified
    version of the same page, with the real render path currently using
    the hardcoded strings). Smaller counts in Landing.jsx,
    PriceForecast.jsx, ProfitCalculator.jsx, Layout.jsx, AskAssistant.jsx.

  NOT YET DONE: fixing AIAdvisor.jsx / Landing / PriceForecast /
  ProfitCalculator hardcoding, and closing the locale gaps. Bulk-
  translating ~1000 keys x 12 languages was deliberately not attempted
  in one pass -- auto-generating that much unreviewed financial/legal
  terminology for a live agri-fintech product is a real accuracy/harm
  risk, not just an incompleteness, and will be approached
  incrementally with the demo-journey screens prioritized first.
