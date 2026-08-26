"""Focused contracts for the human-facing India V1 buildability view."""
from __future__ import annotations

import re
from collections.abc import Mapping

from fastapi.testclient import TestClient

from forge.india_v1.catalog import get_catalog
from forge.india_v1.view_model import compose_buildability_view_model
from server.app import app


CLIENT = TestClient(app)
TARGETS = {
    "MRI": "Magnetic resonance imaging system",
    "5-axis CNC": "5-axis CNC machining center",
    "freeze dryer": "Pharmaceutical freeze dryer/lyophilizer",
    "transformer": "Grid transformer",
    "textile machine": "Textile spinning machine",
}


def test_common_language_spelling_preserves_five_axis_intent() -> None:
    payload = compose_buildability_view_model("5-axis CNC machining centre").to_dict()
    assert payload["title"] == "5-axis CNC machining center"


def _string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _string_values(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _string_values(nested)


def _assert_public_labels_are_clean(payload: Mapping[str, object]) -> None:
    text = "\n".join(_string_values(payload))
    lowered = text.casefold()
    for forbidden in ("reference primitive", "shared:", "product:", "india-v1:", "node:"):
        assert forbidden not in lowered
    # Field names intentionally use a stable JSON contract; this check is for
    # string values, where internal snake-case IDs would leak to the UI.
    snake_values = re.findall(r"(?<![A-Za-z0-9])[a-z][a-z0-9]*_[a-z0-9_]+(?![A-Za-z0-9])", text)
    assert not snake_values, snake_values[:5]
    assert "id" not in payload
    assert "record_id" not in payload
    assert "canonical_name" not in payload


def test_five_representative_products_compose_one_generalized_view() -> None:
    for query, expected_title in TARGETS.items():
        first = compose_buildability_view_model(query).to_dict()
        second = compose_buildability_view_model(query).to_dict()
        assert first == second
        assert first["title"] == expected_title
        assert first["plain_summary"]
        assert first["major_systems"]
        assert first["critical_bottlenecks"]
        assert len(first["critical_bottlenecks"]) <= 7
        assert [step["sequence"] for step in first["localization_path"]] == sorted(
            step["sequence"] for step in first["localization_path"]
        )
        for group in (
            "components",
            "processes",
            "equipment",
            "tooling",
            "materials",
            "metrology",
            "qualification",
            "capabilities",
        ):
            assert isinstance(first[group], list)
        buildability = first["buildability"]
        assert sum(buildability[key] for key in ("available", "partial_or_import_dependent", "missing", "unknown")) == buildability["evaluated_node_count"]
        assert buildability["overall_index"] is None
        _assert_public_labels_are_clean(first)


def test_view_preserves_typed_links_and_is_honest_about_absent_facilities() -> None:
    payload = compose_buildability_view_model("MRI").to_dict()
    assert payload["upstream"]
    assert payload["downstream"] == payload["unlocks"]
    assert payload["related"]
    assert payload["evidence_summary"]
    assert payload["optional_panels"]["facilities"]["state"] == "LIMITED_DATA"
    assert payload["optional_panels"]["map"]["state"] == "LIMITED_DATA"
    assert "facilities" not in payload
    assert "map_points" not in payload


def test_buildability_api_accepts_query_and_exact_id_without_returning_raw_id() -> None:
    catalog = get_catalog()
    record = catalog.search_hits("MRI", limit=1)[0]["record"]
    by_query = CLIENT.get("/api/india/buildability", params={"q": "MRI"})
    by_id = CLIENT.get("/api/india/buildability", params={"record_id": record["id"]})
    alias = CLIENT.get("/api/india/view", params={"q": "MRI"})
    assert by_query.status_code == by_id.status_code == alias.status_code == 200
    assert by_query.json() == by_id.json() == alias.json()
    _assert_public_labels_are_clean(by_query.json())


def test_buildability_api_rejects_empty_and_unknown_subjects() -> None:
    assert CLIENT.get("/api/india/buildability").status_code == 422
    assert CLIENT.get("/api/india/buildability", params={"q": "zzzzzzzzzzzzzzzz"}).status_code == 404
