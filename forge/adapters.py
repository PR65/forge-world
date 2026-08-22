"""FORGE WORLD live data adapters.

Adapters fetch open-licensed data, wrap every field as an EvidenceRecord-classed
observation, and NEVER write into model state without explicit promotion. This module
ships one fully working connector (World Bank Open Data, CC BY-4.0-terms API) and the
interface for future connectors.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from .evidence import EvidenceRecord, Source, snapshot_hash
from .epistemics import Confidence, EpistemicClass, confidence as _conf


class AdapterError(Exception):
    pass


@dataclass
class AdapterResult:
    source: Source
    records: List[EvidenceRecord]
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

        records: List[EvidenceRecord] = []
        notes: List[str] = []
        for row in rows:
            if row.get("value") is None:
                continue
            yr = str(row.get("date"))
            val = float(row["value"])
            records.append(
                EvidenceRecord(
                    claim_id=f"wb.{self.country_iso}.{code}.{yr}",
                    subject=f"{self.country_iso}.{indicator_key}",
                    predicate="observed_value",
                    epistemic_class=EpistemicClass.MEASURED,
                    value_text=f"{val:.0f} ({label}, {yr})",
                    source_ids=(src.id,),
                    publication_date=str(yr),
                    retrieval_date=date.today().isoformat(),
                    geographic_scope=self.country_iso,
                    technical_scope="national accounts aggregate",
                    extraction_method="world_bank_api_v2",
                    confidence=_conf(
                        authority=0.95,
                        directness=1.0,
                        recency=0.9,
                        geographic_specificity=1.0,
                        technical_specificity=0.7,
                        completeness=0.8,
                    ),
                    license=src.license,
                    quote_or_caveat="Official statistical series; revision lag applies",
                )
            )
        if not records:
            notes.append("no non-null rows returned")

        blob = json.dumps(payload, sort_keys=True).encode()
        return AdapterResult(
            source=src,
            records=records,
            raw_payload_hash=snapshot_hash(payload),
            fetched_at=date.today().isoformat(),
            notes=notes,
        )


def run_adapter_demo(country: str = "IND") -> Dict[str, Any]:
    wb = WorldBankAdapter(country)
    out: Dict[str, Any] = {"country": country, "series": {}}
    for key in wb.INDICATORS:
        res = wb.fetch_indicator(key, years=3)
        out["series"][key] = {
            "source": res.source.to_json(),
            "records": [r.to_json() for r in res.records],
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
