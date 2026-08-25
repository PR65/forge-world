from pathlib import Path

from forge.epistemics import EpistemicClass
from forge.model import Project, ProjectStateContribution, STATE_CONTRIBUTION
from forge.pack import load_pack
from forge.optionreport import option_value_report
from forge.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "packs" / "materials_minerals_foundational.yaml"


def test_only_authoritative_glm_import_candidate_is_present_and_loadable():
    assert PACK_PATH.exists()
    assert not (ROOT / "packs" / "materials_minerals_foundational_MANUAL_TEST_DO_NOT_IMPORT.yaml").exists()
    pack = load_pack(PACK_PATH)
    summary = pack.summary()
    assert summary["pack_id"] == "materials_minerals_foundational"
    assert summary["entities"] == 137
    assert summary["evidence"] == 33


def test_materials_evidence_lineage_and_conflicts_remain_explicit():
    pack = load_pack(PACK_PATH)
    for record in pack.evidence.values():
        if record.epistemic_class in {EpistemicClass.MEASURED, EpistemicClass.REPORTED}:
            assert record.source_ids
            for source_id in record.source_ids:
                assert source_id in pack.sources
                assert pack.sources[source_id].license
    assert any(
        record.epistemic_class == EpistemicClass.CONFLICTED
        for record in pack.evidence.values()
    )


def test_nameplate_factors_and_projects_are_not_laundered_into_operating_truth():
    pack = load_pack(PACK_PATH)
    segments = pack.world.of_kind("capacity_segment")
    assert segments
    for segment in segments:
        assert segment.epistemic_class == "ESTIMATED"
        assert all(
            0 <= value <= 1
            for value in (
                segment.availability,
                segment.utilization,
                segment.yield_fraction,
                segment.qualification_fraction,
            )
        )
        assert "ASSUMPTION" in segment.notes
    projects = pack.world.of_kind("project")
    assert projects
    assert all(isinstance(project, Project) for project in projects)
    assert all(
        STATE_CONTRIBUTION[project.state] == ProjectStateContribution.ZERO
        for project in projects
    )


def test_materials_records_enrich_existing_canonical_capabilities_without_merging_identity():
    registry = load_registry()
    rare_earth = registry.nodes["cap:rare-earth-separation"]
    mapped = set(rare_earth.metadata["mapped_pack_ids"])
    assert {"humanoid_india", "materials_minerals_foundational"} <= mapped
    local = registry.nodes["pack:materials_minerals_foundational:rec_ree_separation"]
    assert local.canonical_id == "cap:rare-earth-separation"
    assert local.id != rare_earth.id
    assert rare_earth.epistemic_class == "UNKNOWN"


def test_foundational_pack_does_not_become_a_solver_objective_by_accident():
    pack = load_pack(PACK_PATH)
    assert pack.variants == {}
    assert pack.world.of_kind("product_variant") == []
    assert option_value_report(
        [(pack.pack_id, pack)], units_by_pack={}, dva_by_pack={}
    ) == []
