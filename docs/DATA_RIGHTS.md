# DATA RIGHTS ARCHITECTURE

Licensing is part of the model, not an afterthought (MODEL_CONTRACT C19).

## Rules

1. **License metadata follows the data.** Every `Source` carries `license`; every
   `EvidenceRecord` inherits it. Pack validation fails if MEASURED/REPORTED evidence lacks a
   source record (enforced in `forge/pack.py::_build_evidence`).
2. **Referenced, not mirrored.** Public web pages (IndiaBUILD, manufacturer specs, press
   releases) are stored as URL + access date + extracted claim + caveat. No page text is
   republished beyond short attributed claims needed for provenance.
3. **Restricted enrichment boundary.** Sources that cannot be bundled (ecoinvent, commercial
   networks, paywalled standards) are architecturally excluded from packs; the adapter
   interface (`forge/adapters.py`) defines where a licensed connector would plug in without
   contaminating the distributable core.
4. **Open-data adapters.** The World Bank adapter stores only derived observation records plus
   attribution metadata under CC BY 4.0 terms. Raw payloads are hashed, not archived.
5. **No silent synthetic data.** ASSUMPTION/ESTIMATED values exist only as explicitly labeled
   objects with recorded derivation notes; they can never present as observed reality (C21,
   enforced by pack validation and tests).
6. **Export discipline.** Any future bulk export must filter by license metadata; the
   `license: UNSPECIFIED` default is treated as restricted-by-default.

## Per-source posture (summary)

| Source class | Posture |
|---|---|
| Government releases (PIB, World Bank) | Public domain / CC BY — claims + URLs stored |
| Manufacturer product pages | Referenced claims with access dates; no mirroring |
| News/consultancy articles | Referenced claims, MEDIA-REPORTED/ESTIMATED classes, caveats preserved |
| Supplied research corpus | Internal project use; commercial-aggregation numbers stay ESTIMATED |
| Paywalled standards / licensed databases | Not bundled; identifiers only |

## Known ambiguities preserved

- GEM trackers: CC BY vs CC BY-NC discrepancy between corpus documents — treated as
  attribution-required, non-commercial until verified per tracker (unused in V0 packs).
- IndiaBUILD: catalogue size (10,000) vs mapped count (7,047) and dashboard percentage
  inconsistency preserved as separate site-reported fields rather than reconciled silently.
