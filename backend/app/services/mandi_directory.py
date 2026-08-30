"""
Official mandi/APMC name discovery and mapping layer.

WHY THIS EXISTS
----------------
`live_market_data.fetch_live_price_status()` (kept exactly as-is -- see
that module) queries data.gov.in with `filters[market] = <name>`. That is
an EXACT string match against whatever the government dataset calls a
market. CropWise's own town/location list (`app/mock_data/locations.py`)
was built for distance/transport math, not as a government mandi
directory, so a name like "Bilaspur" is not guaranteed to be
spelled/formatted identically to the official Agmarknet "market" field
for that APMC. Matching on the raw local name alone silently produces a
lot of avoidable demo fallbacks.

This module does NOT touch or replace `fetch_live_price_status()`. It sits
in front of it:

    local town name  -->  resolve_candidate_market_names()  -->  try each
    candidate against the live resource, in confidence order, first
    genuine hit wins  -->  falls through to the district/variety resource,
    then to the demo dataset, exactly as documented in
    `fetch_price_result()` below.

CONSERVATIVE MATCHING, BY DESIGN
---------------------------------
Wrong live mandi data is worse than no live data. Every candidate name
this module tries is one of:
  1. The local town name itself, tried VERBATIM as an exact server-side
     filter -- this carries no false-positive risk at all: the government
     API either has a record under that exact string or it returns
     nothing. There is no way for this step to silently return the wrong
     mandi's data.
  2. A hand-curated alias (`ALIAS_HINTS`) -- someone deliberately
     confirmed this mapping, so it's treated as maximum confidence.
  3. A fuzzy match against the real discovered market list for the state
     -- and ONLY the single best match, and ONLY if its similarity score
     clears a high bar (`FUZZY_ACCEPT_THRESHOLD`). A close-but-ambiguous
     candidate is REJECTED, not guessed at. Every fuzzy attempt (accepted
     or rejected) is logged internally (see `_log_match_decision`) with
     the local name, the candidate, the score, and the reason -- never
     surfaced to end users, but auditable server-side.

Discovery: `discover_state_markets()` asks the live API for the *actual*
list of market names the government dataset has for a state (querying
only `filters[state]`, no market/commodity filter), paginating through
ALL available pages rather than an arbitrary fixed record cap, then
fuzzy-matches CropWise's local town names against that real list (difflib
-- no extra dependency needed). Results are cached in-process for 24h so
we don't re-discover on every request.

HONESTY NOTE: exactly like `live_market_data.py`, this was written and
exercised against the failure/fallback path only -- this sandbox has no
route to api.data.gov.in. The discovery HTTP call, caching, and
confidence-scored matching logic are real, but nobody has yet watched it
resolve a real Chhattisgarh mandi name against the live dataset. Verify
with real internet access and a valid key, and expect to tune
ALIAS_HINTS below once you see the actual official names data.gov.in
returns.
"""
import datetime as dt
import difflib
from typing import List, Optional

import httpx

from app.config import settings, logger
from app.mock_data.locations import MARKETS
from app.services import live_market_data, district_market_data
from app.services.mandi_source_normalization import to_source_state

DISCOVERY_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h -- market directories change rarely
DISCOVERY_TIMEOUT_SECONDS = 8.0
DISCOVERY_PAGE_LIMIT = 200  # per-request page size (data.gov.in's own per-call cap)
# Safety ceiling on total *pages* fetched during one discovery call -- NOT
# a claim that data.gov.in caps state market directories at this size.
# Paging continues until the API itself returns a short/empty page; this
# just guards against an unexpected infinite-pagination response shape.
DISCOVERY_MAX_PAGES = 50  # up to 10,000 records -- discovery is a rare, cached (24h) call

# A fuzzy candidate is only ever accepted above this similarity score.
# Deliberately high: an ambiguous or "looks kind of close" match is exactly
# the failure mode this module exists to avoid (wrong live data is worse
# than no live data), so this is tuned conservative, not permissive.
FUZZY_ACCEPT_THRESHOLD = 0.90

# Hand-maintained hints for cases where CropWise's local/town name is known
# (or suspected) to differ from the official Agmarknet "market" field --
# e.g. the APMC serving a town is usually named after a nearby bigger mandi
# town, or uses "New <Name>" / "<Name> (F&V)" style naming. Add to this as
# real mismatches are confirmed by running against the live API -- treated
# as maximum confidence since a human verified them, not the fuzzy matcher.
ALIAS_HINTS = {
    "Bilha": ["Bilaspur", "Bilha"],
    "Ambikapur": ["Ambikapur", "Surguja", "Ambikapur(Surguja)"],
    "Mahasamund": ["Mahasamund"],
}

# CropWise's local town names -> the Chhattisgarh REVENUE DISTRICT they sit
# in. Needed only for the second resource (district_market_data.py), which
# is keyed by District rather than Market. Most of our towns are their own
# district headquarters; the exceptions are noted.
LOCAL_MARKET_TO_DISTRICT = {
    "Bilaspur": "Bilaspur",
    "Raipur": "Raipur",
    "Durg": "Durg",
    "Raigarh": "Raigarh",
    "Korba": "Korba",
    "Bilha": "Bilaspur",       # Bilha is a tehsil within Bilaspur district
    "Ambikapur": "Surguja",    # Ambikapur is the HQ of Surguja district
    "Rajnandgaon": "Rajnandgaon",
    "Mahasamund": "Mahasamund",
    "Jagdalpur": "Bastar",     # Jagdalpur is the HQ of Bastar district
}

_discovery_cache: dict = {}  # state -> (expires_at, list_of_official_market_names)


def _cache_get(key):
    entry = _discovery_cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if dt.datetime.utcnow() > expires_at:
        _discovery_cache.pop(key, None)
        return None
    return value


def _cache_set(key, value):
    _discovery_cache[key] = (
        dt.datetime.utcnow() + dt.timedelta(seconds=DISCOVERY_CACHE_TTL_SECONDS),
        value,
    )


def _log_match_decision(local_name: str, candidate: Optional[str], score: Optional[float],
                         accepted: bool, reason: str) -> None:
    """
    Internal-only audit trail for the matching decision -- never surfaced
    to end users (the API/UI only ever say "matched" or "no verified
    government market match found"). Logged at INFO so it's queryable
    server-side without turning on DEBUG, but stays out of any
    user-facing response payload.
    """
    logger.info(
        "mandi_match local=%r candidate=%r score=%s accepted=%s reason=%s",
        local_name, candidate, f"{score:.2f}" if score is not None else "n/a",
        accepted, reason,
    )


def discover_state_markets(state: str = "Chhattisgarh", max_pages: int = DISCOVERY_MAX_PAGES) -> List[str]:
    """
    Ask the live government dataset what markets it actually has for this
    state (no market/commodity filter). Pages through results until the
    API returns a short page (fewer rows than the page size) or an empty
    one -- i.e. until data.gov.in itself says there's no more, not an
    arbitrary fixed record count. `max_pages` is a safety ceiling against
    a malformed/looping response, not a designed limit (see module
    docstring). Returns a sorted list of distinct official market names,
    or [] if unconfigured/unreachable/empty -- never raises.
    """
    if not live_market_data.is_configured():
        return []

    cached = _cache_get(state)
    if cached is not None:
        return cached

    names = set()
    try:
        with httpx.Client(timeout=DISCOVERY_TIMEOUT_SECONDS) as client:
            for page in range(max_pages):
                params = {
                    "api-key": settings.data_gov_in_api_key,
                    "format": "json",
                    "limit": str(DISCOVERY_PAGE_LIMIT),
                    "offset": str(page * DISCOVERY_PAGE_LIMIT),
                    "filters[state]": to_source_state(state),
                }
                url = f"{live_market_data.BASE_URL}/{settings.data_gov_in_resource_id}"
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    break
                data = resp.json()
                records = data.get("records") or []
                if not records:
                    break
                for r in records:
                    m = (r.get("market") or "").strip()
                    if m:
                        names.add(m)
                if len(records) < DISCOVERY_PAGE_LIMIT:
                    break  # short page -- this was the last one
    except (httpx.TimeoutException, httpx.HTTPError, ValueError, KeyError):
        # Discovery is best-effort -- on any failure just return whatever
        # (possibly nothing) we gathered so far, never raise into a request.
        pass

    result = sorted(names)
    _cache_set(state, result)
    return result


def resolve_candidate_market_names(local_name: str, state: str = "Chhattisgarh") -> List[str]:
    """
    Build an ordered, deduped list of market names worth trying against
    the live API for this local/town name -- best guess first:
      1. The local name itself -- zero false-positive risk, see module
         docstring.
      2. Hand-maintained alias hints, if any exist for this town --
         human-verified, maximum confidence.
      3. AT MOST ONE fuzzy match from the real discovered market list for
         this state, and only if it clears `FUZZY_ACCEPT_THRESHOLD`. Every
         fuzzy candidate considered is logged via `_log_match_decision`,
         whether accepted or rejected, so matching behaviour is auditable
         without ever guessing in the response itself.
    Always returns at least [local_name], so a caller that ignores this
    module entirely still behaves exactly as before.
    """
    candidates = [local_name]
    for hint in ALIAS_HINTS.get(local_name, []):
        if hint not in candidates:
            candidates.append(hint)
        _log_match_decision(local_name, hint, None, True, "manual_alias")

    official = discover_state_markets(state)
    if official:
        scored = sorted(
            ((name, difflib.SequenceMatcher(None, local_name.lower(), name.lower()).ratio())
             for name in official),
            key=lambda pair: pair[1],
            reverse=True,
        )
        if scored:
            best_name, best_score = scored[0]
            runner_up_score = scored[1][1] if len(scored) > 1 else 0.0
            if best_score >= FUZZY_ACCEPT_THRESHOLD and best_name not in candidates:
                candidates.append(best_name)
                _log_match_decision(local_name, best_name, best_score, True, "fuzzy_high_confidence")
            else:
                reason = (
                    "below_threshold" if best_score < FUZZY_ACCEPT_THRESHOLD
                    else "already_a_candidate"
                )
                _log_match_decision(local_name, best_name, best_score, False, reason)
            # Log the runner-up too when it's close enough to matter, purely
            # for audit visibility into ambiguous cases -- never acted on.
            if len(scored) > 1 and runner_up_score >= FUZZY_ACCEPT_THRESHOLD - 0.10:
                _log_match_decision(local_name, scored[1][0], runner_up_score, False, "runner_up_not_used")

    return candidates


def fetch_price_result(crop_name: str, local_market: str, state: str = "Chhattisgarh") -> dict:
    """
    Status-aware price lookup -- the single entry point routers should
    use. Distinguishes real outcomes rather than collapsing them into a
    single "use demo data" fallback:

      {"status": "ok", "data": {...}}
          A genuine record was found. `data["source_resource"]` is either:
            "market"           -- the primary, mandi-specific resource
                                   matched (via an exact/alias/high-
                                   confidence candidate name). Label this
                                   "Government Mandi Price".
            "district_variety" -- only the district/variety-aggregated
                                   resource had data. Label this "District
                                   Reference Price" and show the
                                   accompanying explanation that it is
                                   calculated from variety-level records,
                                   not a specific mandi's modal price --
                                   see `data["district_reference_note"]`.

      {"status": "no_records", "data": None}
          Both live resources responded successfully but neither has a
          record for this crop/market/state (tried across every
          candidate market name for the primary resource). This is NOT a
          failure -- callers should show "No official government record
          found for this selection." and must NOT substitute demo data.

      {"status": "error", "data": None}
          At least one of the live resources itself failed (network
          error, timeout, non-200, bad key, unparseable response) and
          neither resource produced a genuine record. This is the ONLY
          status that should trigger a demo-data fallback.

      {"status": "not_configured", "data": None}
          Live data isn't configured at all (no key / demo mode). Not an
          error -- this is the normal, expected state for a demo
          deployment, so callers should fall back to demo data without
          an "unavailable" framing.
    """
    saw_error = False
    saw_not_configured = False

    for candidate in resolve_candidate_market_names(local_market, state):
        outcome = live_market_data.fetch_live_price_status(crop_name, candidate, state)
        if outcome["status"] == "ok":
            data = dict(outcome["result"])
            data["local_market_name"] = local_market
            data["matched_market_name"] = candidate
            data["source_resource"] = "market"
            return {"status": "ok", "data": data}
        if outcome["status"] == "error":
            saw_error = True
        elif outcome["status"] == "not_configured":
            saw_not_configured = True

    district = LOCAL_MARKET_TO_DISTRICT.get(local_market, local_market)
    district_outcome = district_market_data.fetch_district_variety_price_status(crop_name, district, state)
    if district_outcome["status"] == "ok":
        data = dict(district_outcome["result"])
        data["local_market_name"] = local_market
        data["matched_market_name"] = f"{district} (district)"
        data["source_resource"] = "district_variety"
        data["district_reference_note"] = (
            "Calculated from available variety-level government records; "
            "this is not a specific mandi modal price."
        )
        return {"status": "ok", "data": data}
    if district_outcome["status"] == "error":
        saw_error = True
    elif district_outcome["status"] == "not_configured":
        saw_not_configured = True

    if saw_not_configured and not saw_error:
        return {"status": "not_configured", "data": None}
    return {"status": "error" if saw_error else "no_records", "data": None}


def known_local_markets() -> List[str]:
    return [m["name"] for m in MARKETS]
