from forge.evidence import ProofGraph
from forge.model import (
    CapacitySegment,
    Entity,
    Facility,
    ForeignSupplySegment,
    Project,
    Qualification,
    Shock,
    World,
)
from forge.shocks import apply_shocks
from forge.solve import ScenarioOptions
from forge.units import Quantity


def _world() -> World:
    world = World()
    world.add(Entity("item", "Item", "part"))
    world.add(Facility("facility", "Facility", "facility"))
    world.add(
        CapacitySegment(
            "domestic",
            "Domestic capacity",
            "capacity_segment",
            item_id="item",
            facility_id="facility",
            nameplate_annual=Quantity(100, "pcs"),
        )
    )
    world.add(
        ForeignSupplySegment(
            "foreign",
            "Foreign capacity",
            "foreign_supply_segment",
            item_id="item",
            origin_country="CHN",
            nameplate_annual=Quantity(200, "pcs"),
        )
    )
    world.add(
        Project(
            "project",
            "Project",
            "project",
            item_id="item",
            years_to_commission=(2, 4),
            commission_year_estimate=2030,
        )
    )
    world.add(
        Qualification(
            "qualification",
            "Qualification",
            "qualification",
            item_id="item",
            latency_months=(6, 12),
        )
    )
    return world


def test_causal_operational_shock_edits_apply_to_cloned_world():
    world = _world()
    shock = Shock(
        "compound_shock",
        "Compound shock",
        "shock",
        shock_id="compound_shock",
        edits=(
            {"type": "remove_country", "country": "CHN"},
            {"type": "material_embargo", "item": "item", "origin": "CHN"},
            {"type": "facility_outage", "facility_id": "facility", "factor": 0.25},
            {"type": "project_delay", "project_id": "project", "years": 2},
            {
                "type": "qualification_delay",
                "qualification_id": "qualification",
                "months": 9,
            },
        ),
    )
    world.add(shock)

    changed, options, report = apply_shocks(
        world, ProofGraph(), [shock.id], ScenarioOptions()
    )

    assert options.import_eligibility["CHN"] == 0
    assert changed.get("foreign").nameplate_annual.value == 0
    assert changed.get("domestic").nameplate_annual.value == 25
    assert changed.get("project").years_to_commission == (4, 6)
    assert changed.get("project").commission_year_estimate == 2032
    assert changed.get("qualification").latency_months == (15, 21)
    assert not report.rejected_edits
    # The base world is still the immutable scenario baseline.
    assert world.get("domestic").nameplate_annual.value == 100
    assert world.get("foreign").nameplate_annual.value == 200
