"""Focused contracts for objective parsing and fail-intelligent resolution."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from forge.india_v1.objective import parse_objective, resolve_objective
from server.app import app


CLIENT = TestClient(app)


def test_parser_retains_visible_manufacturing_context_without_mistaking_axis_count() -> None:
    objective = parse_objective("100 five-axis CNC machines per year in India")
    assert objective.product_query == "five-axis CNC machines"
    assert objective.quantity == 100
    assert objective.cadence == "PER_YEAR"
    assert objective.geography == "INDIA"

    product_only = parse_objective("5-axis CNC machining centre")
    assert product_only.quantity is None
    assert product_only.product_query == "5-axis CNC machining centre"


def test_parser_handles_natural_intent_modifiers_deadline_and_constraints() -> None:
    objective = parse_objective(
        "I want to manufacture approximately 100 high-quality CNC machining centers "
        "per year in India by 2030 without imported controllers"
    )
    assert objective.product_query == "CNC machining centers"
    assert objective.quantity == 100
    assert objective.quantity_is_approximate is True
    assert objective.modifiers == ("High Quality",)
    assert objective.deadline_year == 2030
    assert objective.constraints == ("Without imported controllers",)


def test_strong_objective_resolution_selects_existing_product_without_raw_ids() -> None:
    payload = resolve_objective("100 five-axis CNC machines per year in India")
    objective = payload["objective"]
    resolution = payload["resolution"]
    assert objective["quantity"] == 100
    assert resolution["classification"] in {"EXACT", "STRONG"}
    assert resolution["can_analyze"] is True
    assert resolution["requires_confirmation"] is False
    assert resolution["selected"]["title"] == "5-axis CNC machining center"
    assert resolution["analysis"]["title"] == resolution["selected"]["title"]
    assert "does not prove capacity" in resolution["honesty_note"]
    serialized = json.dumps(payload).casefold()
    for forbidden in ("india-v1:", "product:", "reference primitive", "canonical_name", "record_id"):
        assert forbidden not in serialized


def test_related_result_requires_confirmation_instead_of_silent_navigation() -> None:
    payload = resolve_objective("50 railway traction motors in India")
    resolution = payload["resolution"]
    assert resolution["classification"] == "NEAREST"
    assert resolution["can_analyze"] is False
    assert resolution["requires_confirmation"] is True
    assert resolution["selected"] is None
    assert resolution["analysis"] is None
    assert resolution["nearest"]
    assert resolution["message"].startswith("Exact product not currently mapped.")


def test_unrelated_low_overlap_query_returns_honest_unresolved_state() -> None:
    payload = resolve_objective("molecular unicorn reactor")
    resolution = payload["resolution"]
    assert resolution["classification"] == "UNRESOLVED"
    assert resolution["can_analyze"] is False
    assert resolution["requires_confirmation"] is False
    assert resolution["selected"] is None
    assert resolution["nearest"] is None
    assert resolution["candidates"] == []


def test_unmapped_subtype_can_offer_a_confirmation_required_family_bridge() -> None:
    payload = resolve_objective("progressive cavity pump")
    resolution = payload["resolution"]
    assert resolution["classification"] == "NEAREST"
    assert resolution["can_analyze"] is False
    assert resolution["requires_confirmation"] is True
    assert "pump" in resolution["nearest"]["title"].casefold()
    assert resolution["nearest"]["match_basis"] == "Nearest mapped industrial family"


def test_resolution_api_contract_supports_objectives_and_bounds_inputs() -> None:
    response = CLIENT.get(
        "/api/india/resolve",
        params={"q": "I want to manufacture 20 industrial freeze dryers in India"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["objective"]["quantity"] == 20
    assert payload["objective"]["product_query"] == "industrial freeze dryers"
    assert payload["resolution"]["classification"] == "STRONG"
    assert "freeze dryer" in payload["resolution"]["selected"]["title"].casefold()

    assert CLIENT.get("/api/india/resolve").status_code == 422
    assert CLIENT.get("/api/india/resolve", params={"q": "x" * 301}).status_code == 422
