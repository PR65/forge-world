from scripts.homi_campaign_account import build_accounting


def test_campaign_accounting_closes_every_discovered_artifact_and_corpus():
    report = build_accounting()
    artifacts = report["artifact_accounting"]
    assert artifacts["raw_and_research_artifacts"] == 321
    assert artifacts["unique_hashes"] == 315
    assert artifacts["raw_archive_entries"] == artifacts["byte_matched_entries"] == 254
    assert artifacts["raw_integrity_failures"] == 0
    assert report["corpus_coverage"]["reported_manus_corpora"] == 20
    assert report["corpus_coverage"]["complete"] is True


def test_campaign_accounting_preserves_promotion_and_metric_boundaries():
    report = build_accounting()
    assert report["gate0_staging"]["canonical_promotions"] == 0
    assert report["targeted_research"]["promotions"] == 14
    assert report["targeted_research"]["source_lineage_fraction"] == 1.0
    assert report["targeted_research"]["effective_qualified_capacity_promotions"] == 0
    assert report["generalization"]["ranked_research_tasks"] == 2
    assert set(report["generalization"]["objective_verdicts"].values()) == {
        "NOT_ADJUDICABLE"
    }
