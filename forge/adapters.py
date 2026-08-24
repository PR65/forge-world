"""FORGE WORLD live and deterministic official-data adapters.

Adapters fetch open-licensed data, wrap every field as an EvidenceRecord-classed
observation, and NEVER write into model state without explicit promotion. This module
ships three working pathways: World Bank Open Data, UN Comtrade, and a checked-in
official-record catalog for primary documents that do not expose stable APIs.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .evidence import EvidenceRecord, Source, snapshot_hash
from .epistemics import EpistemicClass
from .ingestion import Observation, Promotion, SourceSnapshot, promote_observation


class AdapterError(Exception):
    pass


@dataclass
class AdapterResult:
    source: Source
    source_snapshot: SourceSnapshot
    observations: List[Observation]
    records: List[EvidenceRecord]
    promotions: List[Promotion]
    raw_payload_hash: str
    fetched_at: str
    notes: List[str]


class WorldBankAdapter:
    """World Bank Open Data API v2 — indicator series for a country.

    Terms: World Bank Open Data API is open under CC BY 4.0 terms (attribution).
    We store only derived observations plus source metadata; no bulk mirroring.
    """

    BASE = "https://api.worldbank.org/v2"

    INDICATORS = {
        "mva_constant_us": ("NV.IND.MANF.CD", "Manufacturing value added (constant 2015 USD)"),
        "population": ("SP.POP.TOTL", "Population, total"),
        "gdp_constant_us": ("NY.GDP.MKTP.KD", "GDP (constant 2015 USD)"),
    }

    def __init__(self, country_iso: str = "IND", timeout: int = 20):
        self.country_iso = country_iso.upper()
        self.timeout = timeout

    def _fetch(self, url: str) -> Any:
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.load(resp)
        except Exception as e:
            raise AdapterError(f"World Bank fetch failed for {url}: {type(e).__name__}: {e}")

    def fetch_indicator(self, indicator_key: str, years: int = 5) -> AdapterResult:
        if indicator_key not in self.INDICATORS:
            raise AdapterError(f"unknown indicator key '{indicator_key}'")
        code, label = self.INDICATORS[indicator_key]
        url = (
            f"{self.BASE}/country/{self.country_iso}/indicator/{code}"
            f"?format=json&per_page={years}&date=2015:2030"
        )
        payload = self._fetch(url)
        if not isinstance(payload, list) or len(payload) < 2:
            raise AdapterError("unexpected World Bank payload shape")
        meta, rows = payload[0], payload[1] or []

        src = Source(
            id=f"wb_{code.lower().replace('.', '_')}",
            name=f"World Bank {label} ({code})",
            publisher="World Bank Open Data",
            url=url,
            source_type="official_statistics_api",
            license="CC BY 4.0 (World Bank Open Data terms)",
            access_date=date.today().isoformat(),
            notes="Fetched via public API; observation-level provenance preserved",
        )

        payload_hash = snapshot_hash(payload)
        source_snapshot = SourceSnapshot(
            source_id=src.id,
            content_hash=payload_hash,
            hash_scope="raw_payload",
            raw_payload_stored=False,
            access_date=src.access_date,
            license=src.license,
            storage_posture="hash_only",
            url=src.url,
            source_type=src.source_type,
            metadata={"name": src.name, "publisher": src.publisher, "notes": src.notes},
        )
        observations: List[Observation] = []
        records: List[EvidenceRecord] = []
        promotions: List[Promotion] = []
        notes: List[str] = []
        for row in rows:
            if row.get("value") is None:
                continue
            yr = str(row.get("date"))
            val = float(row["value"])
            observation = Observation(
                observation_id=f"obs.wb.{self.country_iso}.{code}.{yr}",
                source_snapshot_id=source_snapshot.snapshot_id,
                subject=f"{self.country_iso}.{indicator_key}",
                predicate="observed_value",
                epistemic_class=EpistemicClass.MEASURED,
                value_text=f"{val:.0f} ({label}, {yr})",
                observed_at=yr,
                geographic_scope=self.country_iso,
                technical_scope="national accounts aggregate",
                caveat="Official statistical series; revision lag applies",
                metadata={
                    "publication_date": yr,
                    "extraction_method": "world_bank_api_v2",
                    "confidence": {
                        "authority": 0.95,
                        "directness": 1.0,
                        "recency": 0.9,
                        "geographic_specificity": 1.0,
                        "technical_specificity": 0.7,
                        "completeness": 0.8,
                    },
                },
            )
            record, promotion = promote_observation(
                observation,
                source_snapshot,
                claim_id=f"wb.{self.country_iso}.{code}.{yr}",
                reviewer="world_bank_adapter",
                promoted_at=date.today().isoformat(),
                rationale="Deterministic API row normalization; no model-state mutation",
            )
            observations.append(observation)
            records.append(record)
            promotions.append(promotion)
        if not records:
            notes.append("no non-null rows returned")

        return AdapterResult(
            source=src,
            source_snapshot=source_snapshot,
            observations=observations,
            records=records,
            promotions=promotions,
            raw_payload_hash=payload_hash,
            fetched_at=date.today().isoformat(),
            notes=notes,
        )


class UNComtradeAdapter:
    """UN Comtrade public preview API — trade observations, never capability.

    The adapter deliberately emits the predicate ``reported_trade_flow`` and a
    caveat that forbids promotion to production or qualified supply.  UN Comtrade
    revisions and estimation flags remain in observation metadata.  Raw rows are
    not mirrored; FORGE stores a payload hash and the promoted observation only.
    """

    BASE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def _fetch(self, url: str) -> Any:
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.load(resp)
        except Exception as exc:
            raise AdapterError(
                f"UN Comtrade fetch failed for {url}: {type(exc).__name__}: {exc}"
            ) from exc

    def fetch_trade(
        self,
        *,
        reporter_code: int,
        hs_code: str,
        period: int,
        flow_code: str = "M",
        partner_code: int = 0,
        max_records: int = 500,
    ) -> AdapterResult:
        if flow_code not in {"M", "X"}:
            raise AdapterError("flow_code must be 'M' (imports) or 'X' (exports)")
        if not str(hs_code).isdigit() or not 2 <= len(str(hs_code)) <= 6:
            raise AdapterError("hs_code must be a 2–6 digit HS code")
        params = {
            "period": int(period),
            "reporterCode": int(reporter_code),
            "cmdCode": str(hs_code),
            "flowCode": flow_code,
            "partnerCode": int(partner_code),
            "partner2Code": 0,
            "customsCode": "C00",
            "motCode": 0,
            "maxRecords": max(1, min(int(max_records), 500)),
        }
        url = f"{self.BASE}?{urllib.parse.urlencode(params)}"
        payload = self._fetch(url)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise AdapterError("unexpected UN Comtrade payload shape")
        if payload.get("error"):
            raise AdapterError(f"UN Comtrade API error: {payload['error']}")

        source = Source(
            id=f"uncomtrade_{reporter_code}_{flow_code}_{hs_code}_{period}",
            name=f"UN Comtrade HS {hs_code} {flow_code} flow, reporter {reporter_code}, {period}",
            publisher="United Nations Statistics Division — UN Comtrade",
            url=url,
            source_type="official_trade_statistics_api",
            license="UN Comtrade License Agreement (reference-only derived use; no raw mirroring)",
            access_date=date.today().isoformat(),
            notes=(
                "Public preview API. Trade is evidence of a recorded cross-border flow, not "
                "production capability, qualified supply, domestic value, or available allocation."
            ),
        )
        payload_hash = snapshot_hash(payload)
        source_snapshot = SourceSnapshot(
            source_id=source.id,
            content_hash=payload_hash,
            hash_scope="raw_payload",
            raw_payload_stored=False,
            access_date=source.access_date,
            license=source.license,
            storage_posture="hash_only",
            url=source.url,
            source_type=source.source_type,
            metadata={
                "name": source.name,
                "publisher": source.publisher,
                "license_url": "https://comtradeplus.un.org/LicenseAgreement",
            },
        )
        observations: List[Observation] = []
        records: List[EvidenceRecord] = []
        promotions: List[Promotion] = []
        notes: List[str] = [
            "TRADE_IS_NOT_PRODUCTION_CAPABILITY",
            "preview rows may be aggregate, estimated, revised, or incomplete",
        ]
        for index, row in enumerate(payload["data"]):
            if not isinstance(row, dict):
                continue
            primary_value = row.get("primaryValue")
            net_weight = row.get("netWgt")
            if primary_value is None and net_weight is None:
                continue
            reporter = str(row.get("reporterISO") or reporter_code)
            partner = str(row.get("partnerISO") or partner_code)
            period_value = str(row.get("period") or period)
            subject = f"trade.{reporter}.{partner}.HS{hs_code}.{flow_code}.{period_value}"
            value_text = (
                f"UN Comtrade row: primary value {primary_value!r} USD; net weight "
                f"{net_weight!r} kg; reported={row.get('isReported')!r}; "
                f"net-weight-estimated={row.get('isNetWgtEstimated')!r}."
            )
            observation = Observation(
                observation_id=(
                    f"obs.uncomtrade.{reporter_code}.{partner_code}.{flow_code}."
                    f"{hs_code}.{period_value}.{index}"
                ),
                source_snapshot_id=source_snapshot.snapshot_id,
                subject=subject,
                predicate="reported_trade_flow",
                epistemic_class=EpistemicClass.REPORTED,
                value_text=value_text,
                value_quantity=(float(primary_value), "USD") if primary_value is not None else None,
                observed_at=period_value,
                geographic_scope=reporter,
                technical_scope=f"HS {hs_code}; flow {flow_code}; partner {partner}",
                caveat=(
                    "Trade flow is not production capability, qualified capacity, supplier "
                    "allocation, product-grade compatibility, or recursive domestic value."
                ),
                metadata={
                    "publication_date": period_value,
                    "extraction_method": "un_comtrade_public_preview_api",
                    "classification_code": row.get("classificationCode"),
                    "is_reported": row.get("isReported"),
                    "is_aggregate": row.get("isAggregate"),
                    "is_net_weight_estimated": row.get("isNetWgtEstimated"),
                    "net_weight_kg": net_weight,
                    "confidence": {
                        "authority": 0.9,
                        "directness": 0.9,
                        "geographic_specificity": 0.8,
                        "technical_specificity": 0.45,
                        "completeness": 0.45,
                    },
                },
            )
            record, promotion = promote_observation(
                observation,
                source_snapshot,
                claim_id=(
                    f"uncomtrade.{reporter_code}.{partner_code}.{flow_code}."
                    f"{hs_code}.{period_value}.{index}"
                ),
                reviewer="un_comtrade_adapter",
                promoted_at=date.today().isoformat(),
                rationale=(
                    "Deterministic official trade-row normalization; explicitly barred from "
                    "capacity or capability promotion."
                ),
            )
            observations.append(observation)
            records.append(record)
            promotions.append(promotion)
        if not records:
            notes.append("no usable rows returned")
        return AdapterResult(
            source=source,
            source_snapshot=source_snapshot,
            observations=observations,
            records=records,
            promotions=promotions,
            raw_payload_hash=payload_hash,
            fetched_at=date.today().isoformat(),
            notes=notes,
        )


class OfficialRecordCatalogAdapter:
    """Load explicitly extracted primary-source observations from checked-in YAML."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> List[AdapterResult]:
        if not self.path.exists():
            raise AdapterError(f"official record catalog not found: {self.path}")
        with self.path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        sources = {
            str(row["id"]): row
            for row in raw.get("sources", ()) or ()
            if isinstance(row, dict) and row.get("id")
        }
        observations_by_source: Dict[str, List[Dict[str, Any]]] = {key: [] for key in sources}
        for row in raw.get("observations", ()) or ():
            if not isinstance(row, dict):
                continue
            source_id = str(row.get("source_id", ""))
            if source_id not in sources:
                raise AdapterError(
                    f"official observation '{row.get('id')}' references unknown source '{source_id}'"
                )
            observations_by_source[source_id].append(row)

        results: List[AdapterResult] = []
        for source_id in sorted(sources):
            source_row = sources[source_id]
            source = Source(
                id=source_id,
                name=str(source_row.get("name", source_id)),
                publisher=str(source_row.get("publisher", "")),
                url=str(source_row.get("url", "")),
                source_type=str(source_row.get("source_type", "official_document")),
                license=str(source_row.get("license", "UNSPECIFIED")),
                access_date=str(source_row.get("access_date", "")),
                notes=str(source_row.get("notes", "")),
            )
            source_payload = {
                "source": source.to_json(),
                "observations": observations_by_source[source_id],
            }
            content_hash = snapshot_hash(source_payload)
            snapshot = SourceSnapshot(
                source_id=source.id,
                content_hash=content_hash,
                hash_scope="content",
                raw_payload_stored=False,
                access_date=source.access_date,
                license=source.license,
                storage_posture="checked_in_structured_extraction",
                url=source.url,
                source_type=source.source_type,
                metadata={"name": source.name, "publisher": source.publisher},
            )
            observations: List[Observation] = []
            records: List[EvidenceRecord] = []
            promotions: List[Promotion] = []
            for row in observations_by_source[source_id]:
                try:
                    epistemic = EpistemicClass(str(row.get("epistemic_class", "REPORTED")))
                except ValueError as exc:
                    raise AdapterError(
                        f"bad epistemic class in official observation '{row.get('id')}'"
                    ) from exc
                value_quantity = row.get("value_quantity")
                observation = Observation(
                    observation_id=str(row["id"]),
                    source_snapshot_id=snapshot.snapshot_id,
                    subject=str(row["subject"]),
                    predicate=str(row["predicate"]),
                    value_text=str(row.get("value_text", "")),
                    value_quantity=(
                        (float(value_quantity[0]), str(value_quantity[1]))
                        if isinstance(value_quantity, (list, tuple)) and len(value_quantity) == 2
                        else None
                    ),
                    epistemic_class=epistemic,
                    observed_at=str(row.get("effective_date", "")),
                    geographic_scope=str(row.get("geographic_scope", "GLOBAL")),
                    technical_scope=str(row.get("technical_scope", "")),
                    caveat=str(row.get("caveat", "")),
                    metadata={
                        "publication_date": str(row.get("publication_date", "")),
                        "extraction_method": "checked_in_primary_source_extraction",
                        "confidence": dict(row.get("confidence", {}) or {}),
                    },
                )
                record, promotion = promote_observation(
                    observation,
                    snapshot,
                    claim_id=str(row.get("claim_id", row["id"])),
                    reviewer=str(row.get("reviewer", "official_record_catalog")),
                    promoted_at=str(row.get("promoted_at", source.access_date)),
                    rationale=str(
                        row.get(
                            "promotion_rationale",
                            "Checked-in primary-source extraction reviewed for scope and caveat.",
                        )
                    ),
                )
                observations.append(observation)
                records.append(record)
                promotions.append(promotion)
            results.append(
                AdapterResult(
                    source=source,
                    source_snapshot=snapshot,
                    observations=observations,
                    records=records,
                    promotions=promotions,
                    raw_payload_hash=content_hash,
                    fetched_at=source.access_date,
                    notes=[
                        "deterministic checked-in extraction",
                        "persistent model use still requires explicit entity binding",
                    ],
                )
            )
        return results


def run_adapter_demo(country: str = "IND") -> Dict[str, Any]:
    wb = WorldBankAdapter(country)
    out: Dict[str, Any] = {"country": country, "series": {}}
    for key in wb.INDICATORS:
        res = wb.fetch_indicator(key, years=3)
        out["series"][key] = {
            "source": res.source.to_json(),
            "source_snapshot": res.source_snapshot.to_json(),
            "observations": [observation.to_json() for observation in res.observations],
            "records": [r.to_json() for r in res.records],
            "promotions": [promotion.to_json() for promotion in res.promotions],
            "payload_hash": res.raw_payload_hash,
            "notes": res.notes,
        }
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="IND")
    args = ap.parse_args()
    print(json.dumps(run_adapter_demo(args.country), indent=1)[:4000])
