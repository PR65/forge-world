from __future__ import annotations

from forge.india_v1.objective_compiler import compile_industrial_objective
from forge.india_v1.objective_models import IndustrialObjective, ObjectiveConstraint


def _objective(product: str, quantity: float = 100.0, **kwargs) -> IndustrialObjective:
    return IndustrialObjective(
        objective_type="manufacture",
        product=product,
        quantity=quantity,
        output_unit="units",
        period="year",
        geography="INDIA",
        target_year=2030,
        **kwargs,
    )


def _line(compilation, label: str):
    return next(row for row in compilation.demand_ledger if row["label"] == label)


def test_robot_fixture_derives_demand_and_assumption_labelled_capacity_gap() -> None:
    result = compile_industrial_objective(_objective("industrial robot", 100_000.0))

    servo = _line(result, "Industrial servo motor")
    assert servo["quantity"] == 600_000.0
    assert servo["coefficient_state"] == "ASSUMPTION"
    gap = next(row for row in result.gap_ledger if row["node_id"] == servo["node_id"])
    assert gap["gap_lo"] == gap["gap_hi"] == 350_000.0
    assert gap["coverage_ratio_lo"] == gap["coverage_ratio_hi"] == 250_000.0 / 600_000.0
    capacity = next(row for row in result.capacity_ledger if row["node_id"] == servo["node_id"])
    assert capacity["epistemic_class"] == "ASSUMPTION"


def test_partial_quantification_retains_unknown_and_unknown_is_not_a_bottleneck() -> None:
    result = compile_industrial_objective(_objective("industrial robot", 10.0))

    encoder = _line(result, "Optical or magnetic encoder")
    assert encoder["quantity"] is None
    assert encoder["quantity_state"] == "QUANTITY_UNKNOWN"
    assert encoder["coefficient_state"] == "UNKNOWN"
    assert not any(row["node_id"] == encoder["node_id"] for row in result.bottlenecks)
    assert any(
        row["target"] == encoder["node_id"] and row["reason"] == "QUANTITY_COEFFICIENT_UNKNOWN"
        for row in result.verification_frontier
    )


def test_family_level_requires_confirmation_and_does_not_inherit_capacity() -> None:
    unconfirmed = compile_industrial_objective(_objective("lithium-ion pouch cell", 1_000.0))
    assert unconfirmed.architecture.requires_confirmation is True
    assert unconfirmed.demand_ledger == ()

    confirmed = compile_industrial_objective(
        _objective("lithium-ion pouch cell", 1_000.0, confirm_family=True)
    )
    assert confirmed.resolved_objective["family_level"] is True
    assert all(row["state"] == "UNKNOWN" for row in confirmed.capacity_ledger)
    assert all(row["state"] == "UNKNOWN" for row in confirmed.dependency_ledger)


def test_country_exclusion_stays_unresolved_without_source_geography() -> None:
    result = compile_industrial_objective(
        _objective(
            "industrial robot",
            constraints=(ObjectiveConstraint(kind="avoid_country", value="CHINA"),),
        )
    )

    assert any(row["constraint_effect"] == "UNRESOLVED" for row in result.dependency_ledger)
    assert any(row["reason"] == "CONSTRAINT_EXPOSURE_UNKNOWN" for row in result.verification_frontier)


def test_stages_order_verification_before_capacity_and_integration() -> None:
    result = compile_industrial_objective(_objective("industrial robot", 100_000.0))
    stages = [row["stage"] for row in result.staged_plan]
    assert stages.index("FOUNDATION") < stages.index("CAPACITY_EXPANSION") < stages.index("INTEGRATION")
    integration = next(row for row in result.staged_plan if row["stage"] == "INTEGRATION")
    assert integration["depends_on"]


def test_five_cross_sector_fixtures_and_non_manual_air_jet_loom_compile() -> None:
    products = (
        "industrial robot",
        "grid transformer",
        "5-axis CNC machining center",
        "centrifugal pump",
        "dialysis machine",
        "air-jet loom",
    )
    results = [compile_industrial_objective(_objective(product, 10.0)) for product in products]

    assert all(result.demand_ledger for result in results)
    assert all(any(row["quantity_state"] == "DERIVED" for row in result.demand_ledger) for result in results)
    loom = results[-1]
    assert loom.resolved_objective["family_key"] == "india-v1:11:textile-weaving-machine:air-jet-loom"
    assert any(node.derivation_class.value == "MODELLED" for node in loom.architecture.nodes)


def test_compilation_serialization_is_deterministic() -> None:
    objective = _objective("industrial robot", 20.0)
    assert compile_industrial_objective(objective).to_dict() == compile_industrial_objective(objective).to_dict()
