from __future__ import annotations

import json

from fastapi.testclient import TestClient

from scripts.forge_cli import main
from server.app import app


CLIENT = TestClient(app)


def test_objective_cli_emits_deterministic_json(capsys) -> None:
    argv = [
        "objective", "compile",
        "--product", "industrial robot",
        "--quantity", "100000",
        "--per", "year",
        "--geography", "INDIA",
        "--target-year", "2030",
        "--json",
    ]
    main(argv)
    first = capsys.readouterr().out
    main(argv)
    second = capsys.readouterr().out

    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == "forge-industrial-objective-compilation-v0"
    assert payload["resolved_objective"]["product"] == "industrial robot"
    assert next(row for row in payload["demand_ledger"] if row["label"] == "Industrial servo motor")["quantity"] == 600_000.0


def test_objective_api_compiles_clean_public_contract() -> None:
    response = CLIENT.post(
        "/api/india/objective/compile",
        json={
            "objective": "manufacture",
            "product": "air-jet loom",
            "quantity": 1000,
            "unit": "units",
            "period": "year",
            "geography": "India",
            "target_year": 2030,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_objective"]["family_key"] == "india-v1:11:textile-weaving-machine:air-jet-loom"
    assert payload["demand_ledger"]
    assert all("india_objective::" not in str(row) for row in payload["demand_ledger"])


def test_objective_api_validates_bounds_units_and_constraints() -> None:
    base = {
        "product": "industrial robot",
        "quantity": 100,
        "unit": "units",
        "period": "year",
        "geography": "INDIA",
        "target_year": 2030,
    }
    for patch in (
        {"product": "x" * 241},
        {"quantity": -1},
        {"quantity": "NaN"},
        {"unit": "kg_product"},
        {"target_year": 2201},
        {"constraints": [{"kind": "avoid_country", "value": "X"}] * 13},
    ):
        response = CLIENT.post("/api/india/objective/compile", json={**base, **patch})
        assert response.status_code == 422, patch
