from pathlib import Path

import pytest

from forge.adapters import OfficialRecordCatalogAdapter, UNComtradeAdapter


ROOT = Path(__file__).resolve().parent.parent


def test_official_catalog_runs_snapshot_observation_promotion_pipeline():
    results = OfficialRecordCatalogAdapter(
        ROOT / "data" / "ingestion" / "official_observations.yaml"
    ).load()

    assert len(results) >= 3
    assert sum(len(result.records) for result in results) >= 7
    for result in results:
        assert result.source_snapshot.content_hash
        assert result.source_snapshot.raw_payload_stored is False
        assert result.source_snapshot.storage_posture == "checked_in_structured_extraction"
        assert len(result.observations) == len(result.records) == len(result.promotions)
        assert all(
            promotion.observation_id == observation.observation_id
            for observation, promotion in zip(result.observations, result.promotions)
        )


def test_comtrade_adapter_preserves_trade_not_capability_boundary(monkeypatch):
    payload = {
        "elapsedTime": "0.01 secs",
        "count": 1,
        "data": [
            {
                "period": "2024",
                "reporterISO": "IND",
                "partnerISO": "W00",
                "classificationCode": "H6",
                "primaryValue": 125_000.0,
                "netWgt": 4_200.0,
                "isReported": True,
                "isAggregate": False,
                "isNetWgtEstimated": False,
            }
        ],
        "error": "",
    }
    adapter = UNComtradeAdapter()
    monkeypatch.setattr(adapter, "_fetch", lambda _url: payload)

    result = adapter.fetch_trade(
        reporter_code=699,
        hs_code="8458",
        period=2024,
        flow_code="M",
    )

    assert result.source_snapshot.hash_scope == "raw_payload"
    assert result.source_snapshot.raw_payload_stored is False
    assert result.records[0].predicate == "reported_trade_flow"
    assert "not production capability" in result.records[0].quote_or_caveat.lower()
    assert "TRADE_IS_NOT_PRODUCTION_CAPABILITY" in result.notes


@pytest.mark.parametrize("bad_code", ["x", "1", "1234567"])
def test_comtrade_adapter_rejects_invalid_hs_codes(bad_code):
    with pytest.raises(Exception):
        UNComtradeAdapter().fetch_trade(
            reporter_code=699,
            hs_code=bad_code,
            period=2024,
        )
