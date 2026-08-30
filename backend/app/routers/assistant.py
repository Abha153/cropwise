"""
Global Farm Assistant -- multilingual, voice-first entry point.

Flow (mirrors the architecture requested for the multilingual upgrade):

    text (any supported language)
        -> app.i18n.nlu.parse()            language-neutral intent + entities
        -> intent-specific handler          real business logic per intent,
                                             OR an honest "I don't have that
                                             data" response -- never a guess
        -> app.i18n.templates                native-language response text

Positioning note (see README): this is a deterministic, rule-based
multilingual intent engine -- not a general-purpose LLM. It's fast,
transparent, works offline, and never hallucinates: any intent it can't
genuinely answer from real CropWise data returns an explicit "I don't have
enough reliable data" message instead of making something up.

Critically: if the crop or location can't be identified, this NEVER
silently substitutes a default (no more silent "Tomato" / "Bilaspur") --
it returns a `clarification_needed` field and a native-language question,
and the frontend must ask the user rather than guessing.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas
from app.i18n.nlu import parse
from app.i18n.crop_terms import localized_crop_name
from app.i18n.intents import DISEASE_HELP, QUALITY, TRANSPORT, GENERAL_AGRICULTURE_QUERY
from app.i18n.templates import (
    render_market_recommendation, render_clarify_crop, render_clarify_location,
    render_no_data, render_disease_help, render_transport, render_quality_pointer,
)
from app.i18n.languages import FULLY_SUPPORTED, catalog_as_dicts
from app.routers.market import compare_markets
from app.services.transport_optimizer import estimate_transport_cost

router = APIRouter(prefix="/assistant", tags=["assistant"])

DEFAULT_QUANTITY_KG = 500.0

# Intents CropWise can genuinely answer WITHOUT needing crop+location (a
# real image-analysis pointer, or an honest refusal) -- these skip the
# clarification-required flow below entirely.
NO_ENTITY_NEEDED_INTENTS = {QUALITY, GENERAL_AGRICULTURE_QUERY}


@router.get("/languages")
def assistant_languages():
    """Full language capability matrix -- the frontend's single source of
    truth for which languages to offer and what each one actually supports."""
    return {"languages": catalog_as_dicts(), "fully_supported": FULLY_SUPPORTED}


@router.post("/ask")
def ask(payload: schemas.AssistantAsk, db: Session = Depends(get_db)):
    language = payload.language if payload.language else "en"
    native = language in FULLY_SUPPORTED
    effective_language = language if native else "en"

    parsed = parse(
        payload.question, language=language,
        known_crop=payload.known_crop, known_quantity_kg=payload.known_quantity_kg,
        known_location=payload.known_location,
    )
    intent = parsed["intent"]

    base_response = {
        "understood_language": language,
        "native_response": native,
        "intent": intent,
        "crop": parsed["crop"],
        "quantity_kg": parsed["quantity_kg"],
        "location": parsed["location"],
        "quantity_assumed": False,
        "clarification_needed": None,
        "market_options": [],
    }

    def with_fallback_note(text: str) -> str:
        if not native:
            return text + " (Full understanding for this language is still limited -- English/Hindi work best.)"
        return text

    # --- Intents CropWise genuinely cannot answer: say so, never hallucinate. ---
    if intent == DISEASE_HELP:
        text = with_fallback_note(render_disease_help(effective_language, parsed["crop"]))
        return {**base_response, "answer": text}

    if intent == GENERAL_AGRICULTURE_QUERY:
        text = with_fallback_note(render_no_data(effective_language, parsed["crop"]))
        return {**base_response, "answer": text}

    if intent == QUALITY:
        text = with_fallback_note(render_quality_pointer(effective_language, parsed["crop"]))
        return {**base_response, "answer": text}

    # --- Every remaining intent needs a real crop + location. Never guess. ---
    if "crop" in parsed["missing"]:
        text = with_fallback_note(render_clarify_crop(effective_language))
        return {**base_response, "answer": text, "clarification_needed": "crop"}

    if "location" in parsed["missing"]:
        text = with_fallback_note(render_clarify_location(effective_language))
        return {**base_response, "answer": text, "clarification_needed": "location"}

    quantity_kg = parsed["quantity_kg"]
    quantity_assumed = quantity_kg is None
    if quantity_assumed:
        quantity_kg = DEFAULT_QUANTITY_KG

    comparison = compare_markets(crop=parsed["crop"], quantity_kg=quantity_kg, location=parsed["location"], db=db)
    crop_display = localized_crop_name(parsed["crop"], effective_language)
    if comparison.get("insufficient_data") or not comparison.get("options"):
        answer = with_fallback_note(render_no_data(effective_language, crop=crop_display))
        return {**base_response, "answer": answer, "quantity_kg": quantity_kg, "quantity_assumed": quantity_assumed}
    best = comparison["options"][0]

    # --- TRANSPORT: real transport_optimizer calculation, not a market pitch. ---
    if intent == TRANSPORT:
        transport_cost = estimate_transport_cost(best["distance_km"], quantity_kg)
        answer = with_fallback_note(render_transport(
            effective_language, quantity=f"{quantity_kg:.0f}", crop=crop_display,
            location=parsed["location"], market=best["market"], distance=best["distance_km"],
            transport_cost=f"{transport_cost:,.0f}",
        ))
        return {**base_response, "answer": answer, "quantity_kg": quantity_kg, "quantity_assumed": quantity_assumed}

    # --- Default: MARKET_RECOMMENDATION and every other market-adjacent
    # intent (PRICE_FORECAST/PROFIT_CALCULATION/FARMPOOL/BUYER_SEARCH) all
    # resolve through the same real market-comparison engine, since a net-
    # profit market answer is directly relevant to all of them. ---
    answer = render_market_recommendation(
        effective_language,
        quantity=f"{quantity_kg:.0f}", crop=crop_display, market=best["market"],
        location=parsed["location"], net_profit=f"{best['net_profit']:,.0f}",
        price=best["modal_price_per_kg"], distance=best["distance_km"],
        transport=f"{best['transport_cost']:,.0f}",
    )
    if quantity_assumed:
        assumed_note = {
            "en": f" (assumed {DEFAULT_QUANTITY_KG:.0f} kg since no quantity was mentioned)",
            "hi": f" (मात्रा नहीं बताई गई, इसलिए {DEFAULT_QUANTITY_KG:.0f} किलो मान लिया गया)",
        }.get(effective_language, f" (assumed {DEFAULT_QUANTITY_KG:.0f} kg)")
        answer += assumed_note
    answer = with_fallback_note(answer)

    return {
        **base_response,
        "answer": answer,
        "quantity_kg": quantity_kg,
        "quantity_assumed": quantity_assumed,
        "recommended_market": best["market"],
        "market_options": comparison["options"],
    }
