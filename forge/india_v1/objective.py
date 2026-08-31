"""Human-facing objective parsing and honest India V1 subject resolution.

This module is intentionally a presentation adapter.  It retains simple
objective context (quantity, cadence, geography, and an explicit modifier)
while resolving only against the existing India V1 catalog.  It does not
infer capacity, add catalog records, or promote a merely related result into
an analysis subject without user confirmation.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .catalog import IndiaCatalog, get_catalog
from .view_model import compose_buildability_view_model


OBJECTIVE_RESOLUTION_SCHEMA_VERSION = "forge-india-objective-resolution-v1"

_SPACE = re.compile(r"\s+")
_LEADING_INTENT = (
    re.compile(r"^(?:i|we)\s+(?:want|would\s+like|plan|need)\s+to\s+", re.IGNORECASE),
    re.compile(r"^help\s+(?:me|us)\s+(?:to\s+)?", re.IGNORECASE),
    re.compile(r"^what\s+(?:would|does)\s+it\s+take\s+to\s+", re.IGNORECASE),
    re.compile(r"^can\s+india\s+", re.IGNORECASE),
    re.compile(r"^(?:please\s+)?(?:analy[sz]e|build|make|manufacture|produce|locali[sz]e)\s+", re.IGNORECASE),
)
_GEOGRAPHY = re.compile(r"\b(?:in|within|for)\s+india\b", re.IGNORECASE)
_CADENCE = re.compile(
    r"(?:\s*/\s*(?P<slash>year|yr|month|mo|week|wk|day))"
    r"|(?:\b(?:per|each|a)\s+(?P<word>year|month|week|day)\b)"
    r"|(?P<annual>\bannually\b)",
    re.IGNORECASE,
)
_DEADLINE = re.compile(r"\bby\s+(?P<year>20\d{2}|21\d{2})\b", re.IGNORECASE)
_CONSTRAINT = re.compile(r"\b(?P<prefix>without|excluding)\s+(?P<value>.+)$", re.IGNORECASE)
_MODIFIER = re.compile(r"\b(?P<value>high[- ]quality)\b", re.IGNORECASE)
_APPROXIMATE = re.compile(r"^(?P<value>about|around|roughly|approximately|approx\.?)\s+", re.IGNORECASE)
_QUANTITY = re.compile(
    r"^(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)"
    r"(?:\s*(?P<scale>thousand|million))?"
    # Do not interpret the leading 5 in '5-axis CNC' or 3 in '3 T MRI' as
    # production quantity.
    r"(?!\s*[- ]?axis\b)(?!\s*[Tt]\b)"
    r"(?:\s*(?P<unit>units?|pieces?|sets?|machines?|systems?|GW|MW|kW))?"
    r"\s+(?:of\s+)?",
    re.IGNORECASE,
)

_CADENCE_CODES = {
    "year": ("PER_YEAR", "per year"),
    "yr": ("PER_YEAR", "per year"),
    "month": ("PER_MONTH", "per month"),
    "mo": ("PER_MONTH", "per month"),
    "week": ("PER_WEEK", "per week"),
    "wk": ("PER_WEEK", "per week"),
    "day": ("PER_DAY", "per day"),
}

_STATUS_LABELS = {
    "STRONG": "Strong / available",
    "AVAILABLE": "Available",
    "PARTIAL": "Partial",
    "SCALE_LIMITED": "Scale-limited",
    "IMPORT_DEPENDENT": "Import dependent",
    "MISSING": "Missing",
    "UNKNOWN": "Unknown",
    "CONFLICTED": "Conflicted",
}

_MATCH_BASIS = {
    "exact": "Exact atlas name or alias",
    "phrase": "Full product phrase matched",
    "all_tokens": "All meaningful product terms matched",
    "alias": "Common name or acronym matched",
    "fuzzy": "Close spelling match",
    "partial": "Partial product-name match",
    "related": "Related industrial family",
}

_RESOLUTION_LOW_INFORMATION = {
    "a",
    "an",
    "and",
    "build",
    "center",
    "centre",
    "equipment",
    "industrial",
    "machine",
    "machines",
    "machinery",
    "make",
    "manufacture",
    "of",
    "product",
    "products",
    "system",
    "systems",
    "the",
    "unit",
    "units",
}
_PRODUCT_KINDS = {"PRODUCT", "EQUIPMENT"}
_MIN_DIRECT_COVERAGE = 0.50
_MIN_CANDIDATE_MARGIN = 18.0

# A deliberately small cross-family safety vocabulary, not a product routing
# table.  These modifiers change the underlying machine/component family and
# therefore must occur in the mapped record's own name/aliases before a hit is
# offered.  Everything else is resolved from catalog names, aliases, family
# keys and graph metadata.
_FAMILY_DEFINING_MODIFIERS = frozenset(
    {"ball", "hydraulic", "optical", "plasma", "reaction", "traction", "vacuum", "wind"}
)
_SAFE_FAMILY_HEADS = frozenset(
    {"battery", "cnc", "compressor", "furnace", "motor", "packaging", "pump", "robot", "transformer"}
)
_SAFE_BROADER_MODIFIERS = frozenset({"traction"})
_FAMILY_CONFLICTS = (
    (frozenset({"lithium", "ion"}), frozenset({"flow"})),
)
_SAFE_HEAD_EQUIVALENTS = (
    (frozenset({"cell"}), frozenset({"lithium", "ion", "pouch"}), "battery"),
)


@dataclass(frozen=True)
class ParsedObjective:
    """Visible, deliberately first-order interpretation of a user objective."""

    raw_input: str
    product_query: str
    quantity: int | float | None = None
    quantity_text: str = ""
    quantity_unit: str = ""
    quantity_is_approximate: bool = False
    cadence: str = ""
    cadence_label: str = ""
    geography: str = ""
    geography_label: str = ""
    deadline_year: int | None = None
    modifiers: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["modifiers"] = list(self.modifiers)
        payload["constraints"] = list(self.constraints)
        return payload


def _clean(value: str) -> str:
    return _SPACE.sub(" ", str(value or "")).strip(" \t\r\n,;:.?!")


def _remove_match(text: str, match: re.Match[str]) -> str:
    return _clean(f"{text[:match.start()]} {text[match.end():]}")


def parse_objective(value: str) -> ParsedObjective:
    """Parse only explicit, low-risk context from a manufacturing objective.

    The returned quantity is context, not an assertion that the selected
    catalog record can be produced at that rate.
    """

    raw = _clean(value)
    work = raw
    geography = ""
    geography_label = ""

    if re.match(r"^can\s+india\b", work, re.IGNORECASE) or _GEOGRAPHY.search(work):
        geography = "INDIA"
        geography_label = "India"
    work = _GEOGRAPHY.sub(" ", work)

    for pattern in _LEADING_INTENT:
        updated = pattern.sub("", work, count=1)
        if updated != work:
            work = _clean(updated)
    # A leading intent can expose a second one: "I want to manufacture ...".
    for pattern in _LEADING_INTENT:
        updated = pattern.sub("", work, count=1)
        if updated != work:
            work = _clean(updated)

    constraints: list[str] = []
    constraint_match = _CONSTRAINT.search(work)
    if constraint_match:
        constraint_value = _clean(constraint_match.group("value"))
        if constraint_value:
            constraints.append(f"{constraint_match.group('prefix').capitalize()} {constraint_value}")
        work = _clean(work[: constraint_match.start()])

    deadline_year = None
    deadline_match = _DEADLINE.search(work)
    if deadline_match:
        deadline_year = int(deadline_match.group("year"))
        work = _remove_match(work, deadline_match)

    cadence = ""
    cadence_label = ""
    cadence_match = _CADENCE.search(work)
    if cadence_match:
        cadence_word = cadence_match.group("slash") or cadence_match.group("word")
        if cadence_match.group("annual"):
            cadence_word = "year"
        cadence, cadence_label = _CADENCE_CODES[str(cadence_word).casefold()]
        work = _remove_match(work, cadence_match)

    modifiers: list[str] = []
    for modifier_match in list(_MODIFIER.finditer(work)):
        modifier = modifier_match.group("value").replace("-", " ").title()
        if modifier not in modifiers:
            modifiers.append(modifier)
    work = _MODIFIER.sub(" ", work)
    work = _clean(work)

    quantity_is_approximate = False
    approximate_match = _APPROXIMATE.match(work)
    if approximate_match:
        quantity_is_approximate = True
        work = _clean(work[approximate_match.end() :])

    quantity: int | float | None = None
    quantity_text = ""
    quantity_unit = ""
    quantity_match = _QUANTITY.match(work)
    if quantity_match:
        literal = quantity_match.group("number")
        numeric = float(literal.replace(",", ""))
        scale = (quantity_match.group("scale") or "").casefold()
        if scale == "thousand":
            numeric *= 1_000
        elif scale == "million":
            numeric *= 1_000_000
        quantity = int(numeric) if numeric.is_integer() else numeric
        quantity_text = _clean(" ".join(part for part in (literal, quantity_match.group("scale") or "") if part))
        quantity_unit = _clean(quantity_match.group("unit") or "")
        work = _clean(work[quantity_match.end() :])

    return ParsedObjective(
        raw_input=raw,
        product_query=work,
        quantity=quantity,
        quantity_text=quantity_text,
        quantity_unit=quantity_unit,
        quantity_is_approximate=quantity_is_approximate,
        cadence=cadence,
        cadence_label=cadence_label,
        geography=geography,
        geography_label=geography_label,
        deadline_year=deadline_year,
        modifiers=tuple(modifiers),
        constraints=tuple(constraints),
    )


def _retrieval_query(product_query: str) -> str:
    """Apply a few public-name normalizations without changing catalog data."""

    query = _clean(product_query)
    query = re.sub(
        r"\bcentres?\b",
        lambda match: "centers" if match.group(0).casefold().endswith("s") else "center",
        query,
        flags=re.IGNORECASE,
    )
    for word, digit in (("three", "3"), ("four", "4"), ("five", "5"), ("six", "6")):
        query = re.sub(rf"\b{word}[- ]axis\b", f"{digit}-axis", query, flags=re.IGNORECASE)
    query = re.sub(r"\b([3-6])-?axis\s+CNC\s+machines?\b", r"\1-axis CNC machining center", query, flags=re.IGNORECASE)
    query = re.sub(r"\bMRI\s+machines?\b", "MRI", query, flags=re.IGNORECASE)
    return _clean(query)


def _subject_words(value: Any) -> set[str]:
    words = re.findall(r"[a-z0-9]+", str(value or "").casefold().replace("&", " and "))
    normalized: set[str] = set()
    for word in words:
        if word in _RESOLUTION_LOW_INFORMATION:
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = f"{word[:-3]}y"
        elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        normalized.add(word)
    return normalized


def _record_subject(record: Mapping[str, Any]) -> str:
    # Family label is intentionally first: generated variant axes may contain
    # words such as "battery electric" that describe a tractor configuration,
    # not the subject requested by the user.
    label = str(record.get("family_label") or record.get("display_name") or record.get("canonical_name") or "")
    return re.split(r"\s+[—–]\s+", label, maxsplit=1)[0].strip()


def _record_signature_words(record: Mapping[str, Any]) -> set[str]:
    """Build a product-family signature exclusively from record identity fields."""

    values = [
        record.get("family_label"),
        record.get("display_name"),
        record.get("canonical_name"),
        record.get("family_key"),
        *list(record.get("aliases") or ()),
    ]
    signature: set[str] = set()
    for value in values:
        signature.update(_subject_words(value))
    return signature


def _head_word(words: set[str], query: str) -> str:
    ordered: list[str] = []
    for raw_word in re.findall(r"[a-z0-9]+", str(query).casefold()):
        normalized = _subject_words(raw_word)
        ordered.extend(word for word in normalized if word in words)
    return ordered[-1] if ordered else ""


def _semantic_hit(
    query: str,
    hit: Mapping[str, Any],
) -> dict[str, Any] | None:
    record = hit.get("record") if isinstance(hit.get("record"), Mapping) else {}
    if record.get("is_reference_only"):
        return None
    subject = _record_subject(record)
    query_words = _subject_words(query)
    subject_words = _subject_words(subject)
    signature_words = _record_signature_words(record)
    kind = str(record.get("kind") or "").upper()

    # Objective queries are product-like unless the person explicitly asks
    # for a process, material, or capability.  A dependency bridge must not be
    # promoted into the product merely because its technical name is exact.
    explicit_non_product = bool(re.search(r"\b(?:process|material|capability|technology|skill)\b", query, re.I))
    if not explicit_non_product and kind and kind not in _PRODUCT_KINDS:
        return None

    match_type = str(hit.get("match_type") or "")
    subject_overlap = query_words & subject_words
    direct_overlap = len(query_words & signature_words)
    signature_coverage = direct_overlap / max(1, len(query_words))
    if not subject_overlap and not (
        len(query_words) >= 2
        and match_type in {"exact", "phrase", "all_tokens", "alias"}
        and signature_coverage >= 0.90
    ):
        return None
    direct_coverage = max(len(subject_overlap) / max(1, len(query_words)), signature_coverage if not subject_overlap else 0.0)
    head = _head_word(query_words, query)
    family_compatible = bool(head and head in signature_words and query_words & subject_words)
    missing_definers = (query_words & _FAMILY_DEFINING_MODIFIERS) - signature_words
    if missing_definers:
        return None
    if not family_compatible and direct_coverage < _MIN_DIRECT_COVERAGE:
        return None
    if match_type == "related" and direct_coverage < (1.0 / 3.0):
        return None

    enriched = dict(hit)
    enriched["subject_coverage"] = direct_coverage
    enriched["subject_signature"] = sorted(signature_words)
    enriched["family_compatible"] = family_compatible
    return enriched


def _semantic_hits(query: str, hits: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for hit in hits:
        accepted = _semantic_hit(query, hit)
        if accepted is not None:
            result.append(accepted)
    return result


def _candidate(hit: Mapping[str, Any], catalog: IndiaCatalog) -> dict[str, Any]:
    record = hit["record"]
    raw_title = str(
        record.get("display_name")
        or record.get("family_label")
        or record.get("canonical_name")
        or "Mapped industrial family"
    ).strip()
    title = re.split(r"\s+[—–]\s+", raw_title, maxsplit=1)[0]
    title = re.sub(r"^reference\s+primitive\s*:\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"^(?:(?:cross-domain|foundational|infrastructure)\s+equipment\s*:\s*|"
        r"(?:foundational|infrastructure|equipment|product|system)\s+(?=[a-z]))",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = _clean(title.replace("_", " ")) or "Mapped industrial family"
    status = str(record.get("status") or "UNKNOWN").upper()
    summary = str(record.get("explanation") or record.get("use") or "").strip()
    if re.search(r"\b(?:primitive|deduplicated|source pack|canonical record)\b", summary, re.IGNORECASE):
        summary = str(record.get("use") or "").strip()
    if re.search(r"\b(?:primitive|deduplicated|source pack|canonical record)\b", summary, re.IGNORECASE):
        summary = f"Mapped {str(record.get('kind') or 'industrial capability').casefold()} in the India industrial atlas."
    if len(summary) > 320:
        summary = summary[:317].rstrip() + "..."
    return {
        "title": title,
        "variant": str(record.get("variant_label") or "").strip(),
        "domain": str(record.get("domain") or "Shared industrial foundations").strip(),
        "kind": str(record.get("kind") or "CAPABILITY").upper(),
        "summary": summary,
        "status": status if status in _STATUS_LABELS else "UNKNOWN",
        "status_label": _STATUS_LABELS.get(status, "Unknown"),
        "epistemic_class": str(record.get("status_epistemic_class") or "UNKNOWN").upper(),
        "match_basis": _MATCH_BASIS.get(str(hit.get("match_type") or ""), "Related atlas result"),
    }


def _classification(hit: Mapping[str, Any] | None) -> str:
    if hit is None:
        return "UNRESOLVED"
    match_type = str(hit.get("match_type") or "")
    coverage = min(float(hit.get("coverage") or 0.0), float(hit.get("subject_coverage") or 1.0))
    if match_type == "exact" and coverage >= 0.99:
        return "EXACT"
    if match_type in {"phrase", "all_tokens", "alias"} and coverage >= 0.90:
        return "STRONG"
    # Related hits sharing fewer than half of the meaningful query terms are
    # too weak even for a nearest-family suggestion.
    if bool(hit.get("family_compatible")) and coverage >= 0.50:
        return "NEAREST"
    return "UNRESOLVED"


def resolve_objective(value: str, catalog: IndiaCatalog | None = None, *, candidate_limit: int = 4) -> dict[str, Any]:
    """Resolve an objective without silently accepting a weak catalog hit."""

    catalog = catalog or get_catalog()
    objective = parse_objective(value)
    search_query = _retrieval_query(objective.product_query)
    raw_hits = (
        catalog.search_hits(
            search_query,
            limit=max(12, min(int(candidate_limit) * 6, 48)),
            include_variants=False,
        )
        if search_query
        else []
    )
    hits = _semantic_hits(search_query, raw_hits)[: max(1, min(int(candidate_limit), 8))]
    top = hits[0] if hits else None
    classification = _classification(top)

    # Generic, bounded family inheritance: when a compound subtype is absent,
    # retry only its product-family head.  This is not a per-product routing
    # table and always requires confirmation.  Family-defining modifiers such
    # as "vacuum" or "optical" block inheritance unless explicitly known to
    # remain within the broader family (traction motor is the one current
    # example).
    fallback_used = False
    if classification == "UNRESOLVED" and search_query:
        query_words = _subject_words(search_query)
        head = _head_word(query_words, search_query)
        head = next(
            (
                replacement
                for required, context, replacement in _SAFE_HEAD_EQUIVALENTS
                if required.issubset(query_words) and bool(context & query_words)
            ),
            head,
        )
        missing_definers = query_words & _FAMILY_DEFINING_MODIFIERS
        inheritance_safe = not (missing_definers - _SAFE_BROADER_MODIFIERS)
        if head in _SAFE_FAMILY_HEADS and inheritance_safe:
            fallback_hits = _semantic_hits(
                head,
                catalog.search_hits(
                    head,
                    limit=max(12, min(int(candidate_limit) * 6, 48)),
                    include_variants=False,
                ),
            )[: max(1, min(int(candidate_limit), 8))]
            fallback_hits = [
                hit
                for hit in fallback_hits
                if head in _subject_words(_record_subject(hit["record"]))
                and not any(
                    query_terms.issubset(query_words)
                    and bool(blocked_terms & _subject_words(_record_subject(hit["record"])))
                    for query_terms, blocked_terms in _FAMILY_CONFLICTS
                )
            ]
            if fallback_hits:
                hits = fallback_hits
                top = hits[0]
                classification = "NEAREST"
                fallback_used = True

    # A narrow score margin between different families is a confirmation
    # signal, not permission to auto-select. Exact subject aliases remain exact.
    if classification == "STRONG" and len(hits) > 1:
        top_family = str(top.get("family_key") or top.get("id") or "") if top else ""
        second_family = str(hits[1].get("family_key") or hits[1].get("id") or "")
        margin = float(top.get("score") or 0.0) - float(hits[1].get("score") or 0.0) if top else 0.0
        if top_family != second_family and margin < _MIN_CANDIDATE_MARGIN:
            classification = "NEAREST"

    if classification == "UNRESOLVED":
        # Do not surface a low-overlap result merely because the catalog has a
        # domain prior for one word in the objective.
        candidates: list[dict[str, Any]] = []
    else:
        candidates = []
        seen_titles: set[str] = set()
        for hit in hits[: max(1, min(int(candidate_limit) * 2, 16))]:
            candidate = _candidate(hit, catalog)
            title_key = re.sub(r"[^a-z0-9]+", " ", candidate["title"].casefold()).strip()
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            candidates.append(candidate)
            if len(candidates) >= max(1, min(int(candidate_limit), 8)):
                break
        if fallback_used or classification == "NEAREST":
            candidates = [{**candidate, "match_basis": "Nearest mapped industrial family"} for candidate in candidates]
    selected = candidates[0] if candidates and classification in {"EXACT", "STRONG"} else None
    analysis = compose_buildability_view_model(top["record"], catalog).to_dict() if selected and top else None
    nearest = candidates[0] if candidates and classification == "NEAREST" else None
    if selected:
        message = f"Mapped to {selected['title']} from the existing India industrial atlas."
    elif nearest:
        message = (
            "Exact product not currently mapped. "
            f"Closest mapped industrial family: {nearest['title']}. Review a candidate before analysis."
        )
    else:
        message = (
            "Exact product not currently mapped, and no sufficiently related industrial family was found. "
            "Try a shorter technical product name."
        )

    if objective.quantity is not None or objective.cadence:
        honesty_note = (
            "Quantity and cadence are retained as objective context only. "
            "This V1 atlas does not prove capacity or throughput feasibility."
        )
    else:
        honesty_note = (
            "Catalog resolution identifies a subject for first-order analysis; "
            "it does not by itself prove manufacturing feasibility."
        )

    return {
        "schema_version": OBJECTIVE_RESOLUTION_SCHEMA_VERSION,
        "objective": objective.to_dict(),
        "resolution": {
            "classification": classification,
            "can_analyze": selected is not None,
            "requires_confirmation": nearest is not None,
            "message": message,
            "honesty_note": honesty_note,
            "selected": selected,
            "analysis": analysis,
            "nearest": nearest,
            "candidates": candidates,
        },
    }


__all__ = [
    "OBJECTIVE_RESOLUTION_SCHEMA_VERSION",
    "ParsedObjective",
    "parse_objective",
    "resolve_objective",
]
