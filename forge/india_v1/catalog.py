"""Cached cross-domain catalog and read indexes for the India V1 API.

The four-domain core atlas and the two breadth data packs were authored at
different times and consequently expose slightly different field names.  This
module is the deliberately small adapter boundary: it normalizes the three
packs into one read model, keeps source epistemics intact, and builds indexes
once per process.  It does not assert that a curated ontology node is a
qualified supplier or an effective production capacity.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
import importlib.util
import re
from pathlib import Path
import sys
from threading import Lock
import unicodedata
from typing import Any, Iterable

from .generator import generate_atlas
from .quality import (
    build_making_ladder as _quality_making_ladder,
    correct_epistemic_status as _quality_correct_epistemic_status,
    display_name as _quality_display_name,
    family_key as _quality_family_key,
    variant_label as _quality_variant_label,
)

try:
    from data.india_v1 import domains_05_08 as _domains_05_08
    from data.india_v1 import domains_09_12 as _domains_09_12
except ModuleNotFoundError as exc:  # pragma: no cover - repository imports are the normal path
    if not str(exc).startswith("No module named 'data'"):
        raise
    # ``pytest`` entrypoints can omit the repository root from ``sys.path``.
    # Load the sibling packs by their stable source-local paths, matching the
    # fallback already used by the 01-04 generator.
    _DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "india_v1"

    def _load_pack_module(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ModuleNotFoundError(f"cannot load India V1 data pack at {path}") from exc
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _domains_05_08 = _load_pack_module("_forge_india_v1_domains_05_08", _DATA_ROOT / "domains_05_08.py")
    _domains_09_12 = _load_pack_module("_forge_india_v1_domains_09_12", _DATA_ROOT / "domains_09_12.py")


DEP_GROUPS = ("systems", "processes", "materials", "equipment", "capabilities")
KINDS = ("PRODUCT", "CAPABILITY", "PROCESS", "MATERIAL", "EQUIPMENT")
STATUSES = (
    "STRONG",
    "AVAILABLE",
    "PARTIAL",
    "SCALE_LIMITED",
    "IMPORT_DEPENDENT",
    "MISSING",
    "UNKNOWN",
    "CONFLICTED",
)
EPISTEMIC_CLASSES = (
    "MEASURED",
    "REPORTED",
    "DERIVED",
    "ESTIMATED",
    "MODELLED",
    "ASSUMPTION",
    "SCENARIO",
    "UNKNOWN",
    "CONFLICTED",
)
DEPTH_PROFILE = "V1_BROAD"

DOMAIN_META: dict[str, dict[str, str]] = {
    "01": {"key": "aerospace_space", "name": "Aerospace & Space"},
    "02": {"key": "defense_strategic_manufacturing", "name": "Defense & Strategic Manufacturing"},
    "03": {"key": "energy_nuclear", "name": "Energy & Nuclear"},
    "04": {"key": "electronics_semiconductors_computing", "name": "Electronics, Semiconductors & Computing"},
    "05": {"key": "machines_robotics_automation", "name": "Machines, Robotics, and Industrial Automation"},
    "06": {"key": "materials_metals_chemicals_process", "name": "Materials, Metals, Chemicals, and Process Industries"},
    "07": {"key": "medical_scientific_pharma_biotech_equipment", "name": "Medical, Scientific, Pharma, and Biotech Equipment"},
    "08": {"key": "food_agriculture_biological_production", "name": "Food, Agriculture, and Biological Production Systems"},
    "09": {"key": "09_transport_mobility", "name": "Transport & Mobility"},
    "10": {"key": "10_infrastructure_construction_heavy_equipment", "name": "Infrastructure, Construction, and Heavy Equipment"},
    "11": {"key": "11_consumer_textile_packaging_general_manufacturing", "name": "Consumer, Textile, Packaging, and General Manufacturing"},
    "12": {"key": "12_foundational_industrial_capabilities", "name": "Foundational Industrial Capabilities"},
}
DOMAIN_ORDER = tuple(DOMAIN_META)

_STATUS_MAP = {
    "STRONG / AVAILABLE IN INDIA": "AVAILABLE",
    "AVAILABLE IN INDIA": "AVAILABLE",
    "PARTIAL / SCALE-LIMITED": "SCALE_LIMITED",
    "SPECIFICATION GAP": "PARTIAL",
    "QUALIFICATION GAP": "PARTIAL",
    "CAPACITY GAP": "SCALE_LIMITED",
    "IMPORT-DEPENDENT": "IMPORT_DEPENDENT",
    "MISSING / NO EVIDENCED DOMESTIC CAPABILITY": "MISSING",
    "INDIA_PRESENT_BUT_QUALIFIED_DEPTH_UNKNOWN": "PARTIAL",
    "INDIA_PRESENT_BUT_DEPTH_UNKNOWN": "PARTIAL",
    "INDIA_EMERGING_OR_LIMITED": "SCALE_LIMITED",
    "INDIA_IMPORT_DEPENDENT_OR_QUALIFICATION_UNKNOWN": "IMPORT_DEPENDENT",
    "INDIA_ASSEMBLY_OR_SERVICE_BASE_UNKNOWN": "PARTIAL",
}

_KIND_MAP = {
    "FINISHED_PRODUCT": "PRODUCT",
    "PRODUCT": "PRODUCT",
    "COMPONENT": "PRODUCT",
    "MACHINE": "EQUIPMENT",
    "HEAVY_EQUIPMENT": "EQUIPMENT",
    "EQUIPMENT": "EQUIPMENT",
    "INSTRUMENT": "EQUIPMENT",
    "MATERIAL": "MATERIAL",
    "CHEMICAL": "MATERIAL",
    "CAPABILITY": "CAPABILITY",
    "UTILITY_CAPABILITY": "CAPABILITY",
    "SERVICE_CAPABILITY": "CAPABILITY",
    "PROCESS_CAPABILITY": "PROCESS",
    "PROCESS": "PROCESS",
}

_GROUP_MAP = {
    "system": "systems",
    "systems": "systems",
    "infrastructure": "systems",
    "utility": "systems",
    "utilities": "systems",
    "process": "processes",
    "processes": "processes",
    "proc": "processes",
    "material": "materials",
    "materials": "materials",
    "mat": "materials",
    "equipment": "equipment",
    "equipments": "equipment",
    "machine": "equipment",
    "machines": "equipment",
    "capability": "capabilities",
    "capabilities": "capabilities",
    "cap": "capabilities",
    "design": "capabilities",
    "quality": "capabilities",
    "component": "capabilities",
    "components": "capabilities",
    "service": "capabilities",
}

_REF_PREFIX_MAP = {
    "system": "system",
    "systems": "system",
    "util": "system",
    "utility": "system",
    "material": "material",
    "materials": "material",
    "mat": "material",
    "process": "process",
    "processes": "process",
    "proc": "process",
    "equipment": "equipment",
    "equip": "equipment",
    "capability": "capability",
    "capabilities": "capability",
    "cap": "capability",
}


@lru_cache(maxsize=100_000)
def _normalize_cached(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("&", " and ")
    return re.sub(r"[^\w]+", " ", text, flags=re.UNICODE).strip()


def normalize_text(value: Any) -> str:
    """Normalize user/search text without locale-specific behaviour."""

    return _normalize_cached(str(value or ""))


def _slug(value: Any) -> str:
    text = normalize_text(value).replace(" ", "_")
    return text or "unknown"


@lru_cache(maxsize=100_000)
def _tokens_cached(value: str) -> tuple[str, ...]:
    # Search text treats punctuation, hyphens, and underscores as word
    # boundaries.  IDs remain available through ``normalize_text`` for exact
    # alias lookups, while a user can search ``5-axis`` as ``five axis``.
    text = _normalize_cached(value).replace("_", " ")
    return tuple(dict.fromkeys(part for part in text.split() if part))


def _tokens(value: Any) -> tuple[str, ...]:
    return _tokens_cached(str(value or ""))


# Reusable industrial vocabulary.  These are family-level equivalences, not
# per-query fixtures: the same terms should work for search, discovery, and
# future evidence tasks.  Group tokens are kept separate from literal words so
# an acronym or a common-name alias counts as one semantic match.
_SEARCH_SYNONYM_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mri", ("mri", "mr scanner", "magnetic resonance imaging", "magnetic resonance imaging system")),
    ("ct", ("ct", "ct scanner", "computed tomography", "computed tomography scanner")),
    ("xray", ("x ray", "xray", "x-ray", "radiography", "radiographic system")),
    ("uav", ("uav", "drone", "unmanned aerial vehicle", "unmanned aircraft")),
    ("agriculture", ("agricultural", "agriculture", "farm", "farming", "agri")),
    ("cnc", ("cnc", "computer numerical control")),
    ("machining_center", ("machining center", "machining centre", "vertical machining center", "vmc", "5 axis cnc", "five axis cnc")),
    ("freeze_dryer", ("freeze dryer", "freeze drier", "lyophilizer", "lyophilisation", "lyophilization")),
    ("food_dehydrator", ("food dehydrator", "food dryer", "dehydration system", "dehydrator")),
    ("heat_pump", ("heat pump", "process heat pump", "industrial heat pump")),
    ("electrolyzer", ("electrolyzer", "electrolyser", "water electrolyzer", "hydrogen electrolyzer")),
    ("motor", ("motor", "electric motor", "industrial motor", "industrial electric motor")),
    ("robot", ("robot", "robotic arm", "industrial robot", "robotics")),
    ("humanoid", ("humanoid", "humanoids", "humanoid robot", "bipedal robot", "general purpose robot")),
    ("transformer", ("transformer", "power transformer", "grid transformer")),
    ("packaging", ("packaging machine", "packaging machinery", "packaging line", "packaging equipment")),
    ("textile", ("textile machine", "textile machinery", "spinning machine", "weaving machine")),
    ("pump", ("pump", "centrifugal pump", "process pump", "industrial pump")),
    ("satellite", ("satellite", "spacecraft", "space satellite")),
    ("aircraft", ("aircraft", "airplane", "passenger aircraft", "aeroplane")),
    ("rocket_engine", ("rocket engine", "liquid rocket engine", "launch engine")),
    ("semiconductor", ("semiconductor", "semiconductor device", "chip", "integrated circuit", "ic")),
    ("pcb", ("pcb", "printed circuit board", "printed circuit board assembly", "pcba")),
    ("cmm", ("cmm", "coordinate measuring machine", "coordinate measurement")),
    ("ball_screw", ("ball screw", "ball screws", "ballscrew", "ballscrews", "ball screw manufacturing", "linear motion component")),
    ("bearing", ("bearing", "precision bearing", "rolling bearing")),
    ("ev", ("ev", "electric vehicle", "battery electric vehicle")),
    ("rail", ("rail", "railway", "locomotive", "rolling stock", "metro rail")),
    ("ship", ("ship", "marine", "vessel", "naval vessel")),
    ("construction", ("construction", "heavy equipment", "construction equipment")),
    ("crane", ("crane", "tower crane", "lifting crane")),
    ("water_treatment", ("water treatment", "wastewater treatment", "water purification")),
    ("metrology", ("metrology", "measurement", "calibration", "inspection")),
    ("grinding", ("grinding", "precision grinding", "grinder", "grinding machine")),
    ("heat_treatment", ("heat treatment", "thermal processing", "heat treating")),
    ("nuclear", ("nuclear", "nuclear power", "reactor", "nuclear reactor")),
    ("solar", ("solar", "solar pv", "photovoltaic", "photovoltaics")),
    ("wind", ("wind", "wind turbine", "wind power")),
    ("battery", ("battery", "energy storage", "battery storage")),
    ("food", ("food", "food processing", "food production")),
    ("medical", ("medical", "clinical", "diagnostic", "medical device")),
    ("pharma", ("pharma", "pharmaceutical", "biotech", "biopharmaceutical")),
    ("defense", ("defense", "defence", "military", "strategic manufacturing")),
    ("radar", ("radar", "phased array radar", "airborne radar")),
    ("munition", ("munition", "missile", "loitering munition")),
    ("armored_vehicle", ("armored vehicle", "armoured vehicle", "combat vehicle")),
    ("aircraft_component", ("landing gear", "flight control actuator", "aircraft actuator")),
    ("industrial_gas", ("industrial gas", "gas separation", "air separation")),
    ("additive_manufacturing", ("additive manufacturing", "metal additive manufacturing", "3d printing", "3d printer")),
    ("injection_molding", ("injection molding", "injection moulding", "plastic injection machine")),
    ("pressure_vessel", ("pressure vessel", "composite pressure vessel", "composite overwrapped pressure vessel", "overwrapped pressure vessel", "copv", "pressure")),
    ("star_tracker", ("star tracker", "star sensor", "stellar tracker")),
    ("night_vision", ("night vision", "night-vision", "night vision camera", "low-light camera")),
    ("sonar", ("sonar", "naval sonar", "underwater sonar", "acoustic sonar", "naval")),
    ("accelerometer", ("accelerometer", "mems accelerometer", "mems")),
    ("photolithography", ("photolithography", "lithography", "lithography track")),
    ("harmonic_reducer", ("harmonic reducer", "harmonic drive", "reducer")),
    ("carbon_fiber", ("carbon fiber", "carbon fibre", "carbon fiber prepreg", "prepreg", "carbon")),
    ("technical_ceramic", ("technical ceramic", "advanced ceramic", "alumina ceramic", "alumina", "ceramic")),
    ("ventilator", ("ventilator", "icu ventilator", "mechanical ventilator", "critical care ventilator")),
    ("pet_scanner", ("pet scanner", "positron emission tomography", "isotope scanner")),
    ("seed_drill", ("seed drill", "precision seed drill", "seed planter", "precision planter", "seed")),
    ("rice_transplanter", ("rice transplanter", "rice planter", "rice")),
    ("feed_pelletizer", ("feed pelletizer", "feed pelletiser", "pelletizer", "pelletiser", "feed pellet mill", "feed")),
    ("automatic_transmission", ("automatic transmission", "automatic gearbox", "transmission gearbox", "transmission")),
    ("controllable_propeller", ("controllable pitch propeller", "variable pitch propeller", "controllable propeller")),
    ("rotary_kiln", ("rotary kiln", "cement kiln", "cement rotary kiln", "kiln", "cement")),
    ("refrigerator", ("refrigerator", "fridge", "household refrigerator", "refrigeration appliance", "household")),
    ("shoe_stitching", ("shoe stitching", "shoe upper stitching machine", "footwear stitching", "stitching machine", "stitching")),
    ("robotic_welding", ("robotic welding cell", "welding cell", "robotic weld cell", "robotic welding")),
    ("compressor", ("compressor", "screw compressor", "rotary screw compressor", "industrial compressor", "air compressor")),
    ("sewing", ("sewing", "sewing machine", "industrial sewing machine", "stitching machine", "industrial stitching")),
    ("heat_exchanger", ("heat exchanger", "plate heat exchanger", "plate exchanger", "process heat exchanger")),
    ("elevator_traction", ("elevator traction machine", "traction elevator", "traction machine", "hoist motor", "elevator motor")),
    ("gear_hobbing", ("gear hobbing", "gear hobbing machine", "hobbing machine", "gear hobber", "gear cutting")),
    ("ceramic_kiln", ("ceramic kiln", "kiln furnace", "ceramic furnace", "firing kiln", "kiln")),
    ("vacuum_coating", ("vacuum coating", "vacuum coating machine", "physical vapor deposition", "pvd", "thin film coating", "thin-film deposition")),
    # The atlas currently exposes semiconductor etch/deposition and thin-film
    # process text rather than a dedicated vacuum-coater row.  Keep this as a
    # reusable process family so coating searches can reach that evidence.
    ("thin_film_deposition", ("thin film deposition", "thin films", "etch and deposition", "semiconductor etch and deposition", "physical vapor deposition", "pvd")),
)

_SEARCH_SYNONYM_LOOKUP: dict[str, tuple[str, ...]] = {
    alias: (group, *aliases)
    for group, aliases in _SEARCH_SYNONYM_GROUPS
    for alias in aliases
}
_SEARCH_GROUP_ALIASES: dict[str, tuple[tuple[str, ...], ...]] = {
    group: tuple(sorted((_tokens(alias) for alias in aliases), key=lambda value: (-len(value), value)))
    for group, aliases in _SEARCH_SYNONYM_GROUPS
}
_SEARCH_GROUP_RELATIONS: dict[str, tuple[str, ...]] = {
    # A humanoid is a specialized robot family.  Keeping the relation in the
    # reusable vocabulary permits honest related fallback when the atlas has
    # no dedicated humanoid row without making every robot an exact match.
    "humanoid": ("robot",),
    "star_tracker": ("satellite",),
    "pet_scanner": ("mri",),
    "controllable_propeller": ("ship",),
    "robotic_welding": ("robot",),
    "heat_exchanger": ("heat_pump",),
    "elevator_traction": ("motor", "harmonic_reducer"),
    "ceramic_kiln": ("heat_treatment", "technical_ceramic"),
    "sewing": ("shoe_stitching",),
    "vacuum_coating": ("thin_film_deposition",),
}
_SEARCH_GROUP_EXCLUSIONS: dict[str, tuple[str, ...]] = {
    # ``vessel`` is a broad transport term; in a pressure-vessel query the
    # engineering family should not collapse into ship results.
    "pressure_vessel": ("ship",),
}
_SEARCH_ALIAS_FIRST: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {}
_alias_first_build: dict[str, list[tuple[str, tuple[str, ...]]]] = defaultdict(list)
for _group_name, _group_aliases in _SEARCH_GROUP_ALIASES.items():
    for _alias_tokens in _group_aliases:
        if _alias_tokens:
            _alias_first_build[_alias_tokens[0]].append((_group_name, _alias_tokens))
_SEARCH_ALIAS_FIRST = {
    key: tuple(sorted(values, key=lambda item: (-len(item[1]), item[0], item[1])))
    for key, values in _alias_first_build.items()
}
_LOW_INFORMATION_TERMS = {
    "equipment", "machine", "system", "unit", "line", "plant", "industrial", "production", "manufacturing", "process",
    "per", "year", "years", "annual", "million", "billion", "india", "add", "gw", "generation", "ecosystem", "supply", "chain",
}

# Coarse presentation-domain priors.  They only break ties among candidates
# that already match a meaningful term; they never create supply or an exact
# match.  Several concepts intentionally span domains, so values are tuples.
_DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "aerospace": ("01",), "space": ("01",), "aircraft": ("01",), "airplane": ("01",), "rocket": ("01",), "satellite": ("01",),
    "defense": ("02",), "defence": ("02",), "military": ("02",), "radar": ("02",), "munition": ("02",), "armored": ("02",), "armoured": ("02",), "sonar": ("02",),
    "nuclear": ("03",), "reactor": ("03",), "solar": ("03",), "photovoltaic": ("03",), "wind": ("03",), "electrolyzer": ("03", "06"), "transformer": ("03",), "grid": ("03",), "battery": ("03", "09"), "energy": ("03",),
    "semiconductor": ("04",), "chip": ("04",), "pcb": ("04",), "electronics": ("04",), "wafer": ("04",), "compute": ("04",),
    "cnc": ("05", "12"), "robot": ("05",), "robotics": ("05",), "humanoid": ("05",), "motor": ("05",), "bearing": ("05", "12"), "pump": ("05", "06"), "compressor": ("05",), "actuator": ("05",), "reducer": ("05",),
    "material": ("06",), "steel": ("06",), "alloy": ("06",), "chemical": ("06",), "magnet": ("06",), "heat": ("06",), "electrolyzer": ("06", "03"),
    "mri": ("07",), "medical": ("07",), "clinical": ("07",), "diagnostic": ("07",), "pharma": ("07",), "biotech": ("07",), "freeze": ("07",),
    "food": ("08",), "agricultural": ("08",), "agriculture": ("08",), "farm": ("08",), "grain": ("08",), "dairy": ("08",), "dehydrator": ("08",),
    "vehicle": ("09",), "automotive": ("09",), "electric": ("09",), "ev": ("09",), "rail": ("09",), "railway": ("09",), "marine": ("09",), "ship": ("09",), "locomotive": ("09",),
    "construction": ("10",), "crane": ("10",), "excavator": ("10",), "tunnel": ("10",), "cement": ("10",), "concrete": ("10",), "water": ("10",),
    "textile": ("11",), "packaging": ("11",), "consumer": ("11",), "paper": ("11",), "shoe": ("11",), "apparel": ("11",),
    "metrology": ("12",), "calibration": ("12",), "grinding": ("12",), "precision": ("12",), "machine": ("12",), "tooling": ("12",), "foundational": ("12",),
    "pressure_vessel": ("01",), "star_tracker": ("01",), "night_vision": ("02",), "sonar": ("02",),
    "accelerometer": ("04",), "photolithography": ("04",), "harmonic_reducer": ("05",),
    "carbon_fiber": ("06",), "technical_ceramic": ("06",), "ventilator": ("07",), "pet_scanner": ("07",),
    "seed_drill": ("08",), "rice_transplanter": ("08",), "feed_pelletizer": ("08",),
    "automatic_transmission": ("09",), "controllable_propeller": ("09",), "rotary_kiln": ("10",),
    "refrigerator": ("11",), "shoe_stitching": ("11",), "robotic_welding": ("05",), "ball_screw": ("05", "12"),
    "compressor": ("05", "12"), "sewing": ("11",), "heat_exchanger": ("06",), "elevator_traction": ("10",),
    "gear_hobbing": ("05",), "ceramic_kiln": ("06", "10"), "vacuum_coating": ("04", "12",),
    "thin_film_deposition": ("04",), "harmonic_reducer": ("05",),
}


def _stem_search_token(token: str) -> str:
    """Apply only conservative singular/plural normalization."""

    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ses"):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


_SEARCH_ALIAS_FIRST_STEMMED: dict[str, tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]] = {}
_alias_first_stemmed_build: dict[str, list[tuple[str, tuple[str, ...], tuple[str, ...]]]] = defaultdict(list)
for _group_name, _group_aliases in _SEARCH_GROUP_ALIASES.items():
    for _alias_tokens in _group_aliases:
        if _alias_tokens:
            _alias_stemmed = tuple(_stem_search_token(value) for value in _alias_tokens)
            _alias_first_stemmed_build[_alias_stemmed[0]].append((_group_name, _alias_tokens, _alias_stemmed))
_SEARCH_ALIAS_FIRST_STEMMED = {
    key: tuple(sorted(values, key=lambda item: (-len(item[2]), item[0], item[2])))
    for key, values in _alias_first_stemmed_build.items()
}


def _contains_sequence(tokens: Sequence[str], candidate: Sequence[str]) -> bool:
    if not candidate or len(candidate) > len(tokens):
        return False
    target = tuple(_stem_search_token(value) for value in candidate)
    source = tuple(_stem_search_token(value) for value in tokens)
    return any(source[index : index + len(target)] == target for index in range(len(source) - len(target) + 1))


@lru_cache(maxsize=200_000)
def _semantic_units_cached(value: str) -> frozenset[str]:
    raw = tuple(_tokens(value))
    stemmed = tuple(_stem_search_token(token) for token in raw)
    units = {token for token in stemmed if token not in _LOW_INFORMATION_TERMS}
    checked_groups: set[str] = set()
    for index, token in enumerate(stemmed):
        for group, alias, alias_stemmed in _SEARCH_ALIAS_FIRST_STEMMED.get(token, ()):
            if group in checked_groups:
                continue
            end = index + len(alias_stemmed)
            if end <= len(stemmed) and stemmed[index:end] == alias_stemmed:
                checked_groups.add(group)
                units.difference_update(alias_stemmed)
                units.add(f"@{group}")
    for group in tuple(checked_groups):
        units.update(f"@{related}" for related in _SEARCH_GROUP_RELATIONS.get(group, ()))
        units.difference_update(f"@{excluded}" for excluded in _SEARCH_GROUP_EXCLUSIONS.get(group, ()))
    return frozenset(units)


def _semantic_units(value: Any) -> frozenset[str]:
    return _semantic_units_cached(str(value or ""))


def _semantic_group_labels(units: Iterable[str]) -> list[str]:
    return sorted(value[1:] if value.startswith("@") else value for value in units)


def _domain_hints(value: Any) -> set[str]:
    hints: set[str] = set()
    units = _semantic_units(value)
    for unit in units:
        key = unit[1:] if unit.startswith("@") else unit
        hints.update(_DOMAIN_HINTS.get(key, ()))
    for token in _tokens(value):
        if token not in _LOW_INFORMATION_TERMS:
            hints.update(_DOMAIN_HINTS.get(token, ()))
    return hints


def _edit_distance_one(left: str, right: str) -> bool:
    if left == right:
        return False
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) <= 1
    if len(left) > len(right):
        left, right = right, left
    index_left = index_right = differences = 0
    while index_left < len(left) and index_right < len(right):
        if left[index_left] != right[index_right]:
            differences += 1
            index_right += 1
            if differences > 1:
                return False
        else:
            index_left += 1
            index_right += 1
    return True


def _as_dict(record: Any) -> dict[str, Any]:
    # AtlasRecord is a frozen dataclass.  Its fields already contain the
    # normalized core shape; avoiding ``to_dict`` here saves a second deep
    # serialization pass over the 3,793 core rows during API cold start.
    if hasattr(record, "__dataclass_fields__") and hasattr(record, "id"):
        return dict(vars(record))
    if isinstance(record, Mapping):
        return dict(record)
    to_dict = getattr(record, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    raise TypeError(f"India V1 record is not mapping-like: {type(record)!r}")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


@lru_cache(maxsize=100_000)
def _clean_string_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in values if item and item.strip()))


def _string_list(value: Any) -> list[str]:
    result: list[str] = []
    if value is None:
        return result
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Mapping):
        values = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = (value,)
    if isinstance(values, (list, tuple)) and all(isinstance(item, str) for item in values):
        return list(_clean_string_tuple(tuple(values)))
    for item in values:
        if isinstance(item, str):
            text = item.strip()
            if text and text not in result:
                result.append(text)
            continue
        if isinstance(item, Mapping):
            item = item.get("note") or item.get("text") or item.get("purpose") or item.get("id")
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _status(value: Any) -> str:
    text = str(value or "UNKNOWN").strip()
    if text in STATUSES:
        return text
    mapped = _STATUS_MAP.get(text.upper())
    if mapped:
        return mapped
    return "UNKNOWN"


def _kind(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return _KIND_MAP.get(text, "CAPABILITY")


def _domain_code(row: Mapping[str, Any]) -> str:
    for value in (row.get("domain_code"), row.get("domain_number"), row.get("domain_number")):
        if value not in (None, ""):
            try:
                code = f"{int(value):02d}"
            except (TypeError, ValueError):
                code = str(value).strip()
            if code in DOMAIN_META:
                return code
    domain_id = str(row.get("domain_id") or "")
    if domain_id[:2].isdigit() and domain_id[:2] in DOMAIN_META:
        return domain_id[:2]
    domain_name = normalize_text(row.get("domain") or row.get("domain_name"))
    for code, meta in DOMAIN_META.items():
        if domain_name in {normalize_text(meta["name"]), normalize_text(meta["key"])}:
            return code
    return "shared"


def _domain_name(code: str, row: Mapping[str, Any]) -> str:
    if code in DOMAIN_META:
        return DOMAIN_META[code]["name"]
    return str(row.get("domain") or row.get("domain_name") or "shared_foundations")


def _status_basis(row: Mapping[str, Any]) -> str:
    basis = row.get("status_basis") or row.get("india_status_basis") or row.get("epistemic_basis")
    if isinstance(basis, Mapping):
        basis = basis.get("basis") or basis.get("text")
    text = str(basis or "").strip()
    return text or "Curated India V1 navigation overlay; qualified depth and effective capacity remain UNKNOWN."


def _epistemic(row: Mapping[str, Any]) -> str:
    value = (
        row.get("status_epistemic_class")
        or row.get("epistemic_class")
        or row.get("india_status_epistemic")
    )
    text = str(value or "UNKNOWN").strip().upper()
    return text if text in EPISTEMIC_CLASSES else "UNKNOWN"


def _dependencies(row: Mapping[str, Any]) -> dict[str, list[str]]:
    raw = row.get("dependencies")
    if not isinstance(raw, Mapping):
        raw = row.get("dependency_groups")
    groups = {group: [] for group in DEP_GROUPS}
    if isinstance(raw, Mapping) and set(raw).issubset(DEP_GROUPS):
        # Core and domains 05-08 already use the common five-group contract.
        # Preserve the lists directly; reference canonicalization happens in
        # ``_normalize_refs`` and does not require another group pass.
        return {
            group: list(raw.get(group, ())) if isinstance(raw.get(group, ()), (list, tuple)) else _string_list(raw.get(group))
            for group in DEP_GROUPS
        }
    if isinstance(raw, Mapping):
        iterator = raw.items()
    elif isinstance(raw, Sequence) and not isinstance(raw, str):
        pairs = []
        for item in raw:
            if isinstance(item, Mapping):
                pairs.append((item.get("group"), item.get("ids")))
        iterator = pairs
    else:
        iterator = []
    for source_group, values in iterator:
        target_group = _GROUP_MAP.get(str(source_group or "").casefold(), "capabilities")
        for value in _string_list(values):
            if value not in groups[target_group]:
                groups[target_group].append(value)
    if not any(groups.values()):
        for value in _string_list(row.get("dependency_ids")):
            groups["capabilities"].append(value)
    return groups


def _ladder(row: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    raw = row.get("making_ladder") or row.get("making_ladder_detail") or []
    result: list[dict[str, Any]] = []
    actions = {"IMPORT", "DEVELOP", "LICENSE", "JV", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"}
    raw_items = raw if isinstance(raw, (list, tuple)) else _as_list(raw)
    for index, item in enumerate(raw_items, start=1):
        if isinstance(item, Mapping):
            action = str(item.get("action") or "DEVELOP").strip().upper()
            text = item.get("purpose") or item.get("text") or item.get("step") or ""
            condition = str(item.get("condition") or "").strip()
            sequence = item.get("sequence") or item.get("step") or index
        elif hasattr(item, "action"):
            action = str(getattr(item, "action", "DEVELOP")).strip().upper()
            text = getattr(item, "purpose", "") or getattr(item, "text", "") or ""
            condition = str(getattr(item, "condition", "") or "").strip()
            sequence = getattr(item, "sequence", index)
        else:
            action = "DEVELOP"
            text = str(item)
            condition = ""
            sequence = index
        if action not in actions:
            action = "DEVELOP"
        result.append(
            {
                "sequence": int(sequence) if str(sequence).isdigit() else index,
                "action": action,
                "purpose": str(text or f"Advance the route for {name}.").strip(),
                "condition": condition or "Requires an explicit specification, owner, and acceptance basis.",
            }
        )
    if not result:
        for index, action in enumerate(("IMPORT", "DEVELOP", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"), start=1):
            result.append(
                {
                    "sequence": index,
                    "action": action,
                    "purpose": f"{action.title()} the route for {name}.",
                    "condition": "Requires explicit specification, qualification, and residual-dependence controls.",
                }
            )
    return result


def _reference_id(value: str) -> str:
    """Collapse readable primitive spellings while preserving family refs."""

    text = str(value).strip()
    if not text:
        return "reference:unknown"
    prefix, separator, suffix = text.partition(":")
    normalized_prefix = _REF_PREFIX_MAP.get(prefix.casefold())
    if normalized_prefix and separator:
        return f"shared:{normalized_prefix}:{_slug(suffix)}"
    # ``node:09:foo`` and ``product:05:foo`` are family-level references from
    # the sibling packs.  They are not silently treated as a particular
    # variant; retaining the readable source in a bridge ID keeps that
    # uncertainty auditable and navigable.
    if separator:
        return f"reference:{_slug(text)}"
    return f"reference:{_slug(text)}"


def _family_label(record: Mapping[str, Any]) -> str:
    # Keep the family label aligned with the shared quality display helper.
    # The display helper retains a compact variant suffix; the family label
    # intentionally removes that suffix for grouping and UI explanation.
    name = str(record.get("display_name") or _quality_display_name(record) or record.get("id") or "").strip()
    return re.split(r"\s+[—-]\s+", name, maxsplit=1)[0].strip()


def _family_representative_rank(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """Static fallback ordering; query-specific scoring may pick another variant."""

    kind_rank = {"PRODUCT": 0, "EQUIPMENT": 1, "MATERIAL": 2, "PROCESS": 3, "CAPABILITY": 4}.get(str(record.get("kind")), 5)
    status_rank = {"STRONG": 0, "AVAILABLE": 1, "PARTIAL": 2, "SCALE_LIMITED": 3, "IMPORT_DEPENDENT": 4, "MISSING": 5, "UNKNOWN": 6, "CONFLICTED": 7}.get(str(record.get("status")), 8)
    return (
        bool(record.get("is_reference_only")),
        kind_rank,
        status_rank,
        len(str(record.get("canonical_name", ""))),
        str(record.get("id", "")),
    )


def _normalize_refs(
    values: Any,
    ids: set[str],
    cache: dict[str, str],
    sequence_cache: dict[tuple[str, ...], tuple[str, ...]],
) -> list[str]:
    # Most generated variants reuse exactly the same bounded dependency tuple.
    # Cache the normalized sequence so the 12k-row adapter does not repeat the
    # same prefix/slug work for every compatible axis.
    if values is None or values == () or values == [] or values == "":
        return []
    if isinstance(values, (list, tuple)):
        # Generated packs guarantee reference lists are strings.  Avoid the
        # repeated ``all(isinstance(...))`` scan here; this function is called
        # for every dependency group on every compatible variant.
        raw_values = tuple(value for value in values if value)
    else:
        raw_values = tuple(_string_list(values))
    cached = sequence_cache.get(raw_values)
    if cached is not None:
        return list(cached)
    result: list[str] = []
    for value in raw_values:
        if value in ids:
            ref = value
        else:
            ref = cache.get(value)
            if ref is None:
                ref = _reference_id(value)
                cache[value] = ref
        if ref not in result:
            result.append(ref)
    sequence_cache[raw_values] = tuple(result)
    return result


def _normalize_row(
    raw: Mapping[str, Any],
    ids: set[str],
    reference_cache: dict[str, str],
    sequence_cache: dict[tuple[str, ...], tuple[str, ...]],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    row = dict(raw)
    record_id = str(row.get("id") or row.get("record_id") or row.get("canonical_id") or "").strip()
    if not record_id:
        raise ValueError("India V1 record is missing a stable id")
    code = _domain_code(row)
    name = str(row.get("canonical_name") or row.get("name") or record_id).strip()
    aliases = _string_list(row.get("aliases"))
    if not aliases:
        aliases = [name]
    search_aliases = tuple(dict.fromkeys((*aliases, name, record_id, str(row.get("archetype_id") or ""))))
    deps = _dependencies(row)
    # The core 01-04 generator has already resolved every dependency and graph
    # edge to a canonical ID.  Avoid a second normalization pass for those
    # rows; the sibling packs still take the bridge path below.
    core_resolved = str(row.get("source_spec") or "") == "data.india_v1.domains_01_04"
    if core_resolved:
        normalized_deps = {group: list(deps[group]) for group in DEP_GROUPS}
        dependency_ids = [ref for group in DEP_GROUPS for ref in normalized_deps[group]]
        upstream = _string_list(row.get("upstream") or row.get("upstream_links"))
        downstream = _string_list(row.get("downstream") or row.get("downstream_links"))
        related = _string_list(row.get("related") or row.get("related_links"))
    else:
        normalized_deps = {
            group: _normalize_refs(values, ids, reference_cache, sequence_cache) for group, values in deps.items()
        }
        dependency_ids = [ref for group in DEP_GROUPS for ref in normalized_deps[group]]
        upstream = _normalize_refs([*(_string_list(row.get("upstream") or row.get("upstream_links"))), *dependency_ids], ids, reference_cache, sequence_cache)
        downstream = _normalize_refs(row.get("downstream") or row.get("downstream_links"), ids, reference_cache, sequence_cache)
        related = _normalize_refs(row.get("related") or row.get("related_links"), ids, reference_cache, sequence_cache)
    gaps = _string_list(row.get("gaps") or row.get("gap_notes"))
    imports = _string_list(row.get("import_notes"))
    gap_notes = row.get("gap_import_notes") or row.get("gaps_import_notes")
    if isinstance(gap_notes, Sequence) and not isinstance(gap_notes, str):
        gap_notes = " ".join(_string_list(gap_notes))
    gap_text = str(gap_notes or "").strip()
    if not gap_text:
        gap_text = " ".join((*gaps, *imports)).strip()
    status = _status(row.get("status") or row.get("india_status"))
    normalized = {
        "id": record_id,
        "canonical_name": name,
        "family_key": _quality_family_key(record_id),
        "family_label": _family_label({"canonical_name": name, "id": record_id}),
        "aliases": aliases,
        "domain_code": code,
        "domain_id": code,
        "domain_key": DOMAIN_META.get(code, {}).get("key", "shared_foundations"),
        "domain": _domain_name(code, row) if code != "shared" else "shared_foundations",
        "category": str(row.get("category") or "industrial capability").strip(),
        "kind": _kind(row.get("kind")),
        "explanation": str(row.get("explanation") or "Curated India V1 industrial ontology record.").strip(),
        "uses": _string_list(row.get("uses") or row.get("use")),
        "status": status,
        "status_epistemic_class": _epistemic(row),
        "status_basis": _status_basis(row),
        "dependencies": normalized_deps,
        "dependency_ids": dependency_ids,
        "gaps": gaps,
        "import_notes": imports,
        "gap_import_notes": gap_text,
        "making_ladder": _ladder(row, name),
        "upstream": upstream,
        "downstream": downstream,
        "related": related,
        "source_spec": str(row.get("source_spec") or row.get("source_basis") or "india_v1"),
        "is_reference_only": False,
        "_search_aliases": search_aliases,
    }
    # Correct only unsupported assumption-backed extremes before any status
    # or search indexes are built.  The helper returns a copy and preserves
    # prior labels in auditable metadata when it downgrades to UNKNOWN.
    if normalized["status"] in {"STRONG", "MISSING"} and normalized["status_epistemic_class"] == "ASSUMPTION":
        normalized = _quality_correct_epistemic_status(normalized)
    normalized["family_key"] = _quality_family_key(normalized)
    normalized["family_label"] = _family_label(normalized)
    normalized["variant_label"] = _quality_variant_label(normalized)
    normalized["display_name"] = _quality_display_name(normalized)
    return normalized, search_aliases


def _stub_record(record_id: str) -> dict[str, Any]:
    prefix, _, suffix = record_id.partition(":")
    kind = {
        "shared": {
            "system": "CAPABILITY",
            "process": "PROCESS",
            "material": "MATERIAL",
            "equipment": "EQUIPMENT",
            "capability": "CAPABILITY",
        }.get(suffix.partition(":")[0], "CAPABILITY"),
    }.get(prefix, "CAPABILITY")
    label = suffix.replace(":", " ").replace("_", " ").replace("-", " ").strip() or record_id
    name = f"Reference primitive: {label}"
    ladder = [
        {"sequence": index, "action": action, "purpose": f"{action.title()} the unresolved reference route for {label}.", "condition": "The bridge is a navigation reference; qualification remains UNKNOWN."}
        for index, action in enumerate(("IMPORT", "DEVELOP", "LICENSE", "JV", "BUILD", "SUBSTITUTE", "REDESIGN", "R&D"), start=1)
    ]
    return {
        "id": record_id,
        "canonical_name": name,
        "family_key": _quality_family_key(record_id),
        "family_label": _family_label({"canonical_name": name, "id": record_id}),
        "aliases": [record_id, label],
        "domain_code": "shared",
        "domain_id": "shared",
        "domain_key": "shared_foundations",
        "domain": "shared_foundations",
        "category": "reference primitive",
        "kind": kind,
        "explanation": "A readable bridge for a dependency named by a breadth domain pack; it is not a producer or supply claim.",
        "uses": ["Navigate the dependency graph and identify the evidence task for this primitive."],
        "status": "UNKNOWN",
        "status_epistemic_class": "UNKNOWN",
        "status_basis": "Reference-only bridge created because the source pack names a primitive without a canonical V1 record; capability and supply remain UNKNOWN.",
        "dependencies": {group: [] for group in DEP_GROUPS},
        "dependency_ids": [],
        "gaps": ["Canonical specification, owner, qualification, and effective capacity are UNKNOWN."],
        "import_notes": ["Reference identity is not evidence of domestic availability or production."],
        "gap_import_notes": "Canonical specification, owner, qualification, and effective capacity are UNKNOWN.",
        "making_ladder": ladder,
        "upstream": [],
        "downstream": [],
        "related": [],
        "source_spec": "reference_bridge",
        "is_reference_only": True,
        "_search_aliases": (record_id, label),
    }


def _direct_rows() -> list[dict[str, Any]]:
    atlas_rows = [_as_dict(item) for item in generate_atlas().records]
    rows = atlas_rows + [dict(item) for item in _domains_05_08.ALL_RECORDS] + [dict(item) for item in _domains_09_12.ALL_RECORDS]
    # All direct IDs are known before references are normalized, so a sibling
    # pack can point at a variant generated by another pack without creating a
    # duplicate bridge node.
    ids = {str(row.get("id") or row.get("record_id") or row.get("canonical_id") or "") for row in rows}
    normalized: list[dict[str, Any]] = []
    reference_cache: dict[str, str] = {}
    sequence_cache: dict[tuple[str, ...], tuple[str, ...]] = {}
    for raw in rows:
        item, _ = _normalize_row(raw, ids, reference_cache, sequence_cache)
        normalized.append(item)
    return normalized


@dataclass(frozen=True)
class IndiaCatalog:
    """Immutable-ish read catalog with precomputed deterministic indexes."""

    records: tuple[dict[str, Any], ...]
    by_id: dict[str, dict[str, Any]]
    token_index: dict[str, tuple[str, ...]]
    alias_index: dict[str, tuple[str, ...]]
    domain_index: dict[str, tuple[str, ...]]
    kind_index: dict[str, tuple[str, ...]]
    status_index: dict[str, tuple[str, ...]]
    domain_aliases: dict[str, str]
    search_fields: dict[str, tuple[str, ...]]
    normalized_fields: dict[str, tuple[str, ...]]
    search_token_sets: dict[str, frozenset[str]]
    direct_record_count: int
    # Semantic search indexes.  Defaults keep the adapter constructible for
    # lightweight downstream callers that used the earlier read model.
    search_term_index: dict[str, tuple[str, ...]] = field(default_factory=dict)
    search_name_term_sets: dict[str, frozenset[str]] = field(default_factory=dict)
    search_field_term_sets: dict[str, dict[str, frozenset[str]]] = field(default_factory=dict)
    family_members: dict[str, tuple[str, ...]] = field(default_factory=dict)
    family_representatives: dict[str, str] = field(default_factory=dict)
    family_alias_index: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def reference_record_count(self) -> int:
        return len(self.records) - self.direct_record_count

    @property
    def domain_counts(self) -> dict[str, int]:
        return {
            code: sum(1 for record in self.records if not record["is_reference_only"] and record["domain_code"] == code)
            for code in DOMAIN_ORDER
        }

    @property
    def kind_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(record["kind"] for record in self.records).items()))

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(record["status"] for record in self.records).items()))

    @property
    def epistemic_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(record["status_epistemic_class"] for record in self.records).items()))

    def resolve_domain(self, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        key = normalize_text(value).replace(" ", "_")
        return self.domain_aliases.get(key)

    def ranked_search(
        self,
        query: str = "",
        *,
        domain: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        limit: int = 25,
        include_variants: bool = False,
    ) -> list[tuple[dict[str, Any], int]]:
        """Return deterministic ranked records using the semantic search index.

        ``ranked_search`` remains the compatibility pair-returning API used by
        older callers.  New callers that need explainability should use
        :meth:`search_hits`, which exposes ``match_type`` and ``matched_on``.
        Family grouping is on by default: variants remain searchable, but a
        broad query receives one strongest representative per family instead
        of ten generated siblings.
        """

        return [
            (hit["record"], int(hit["score"]))
            for hit in self.search_hits(
                query,
                domain=domain,
                kind=kind,
                status=status,
                limit=limit,
                include_variants=include_variants,
            )
        ]

    def search_hits(
        self,
        query: str = "",
        *,
        domain: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        limit: int = 25,
        include_variants: bool = False,
    ) -> list[dict[str, Any]]:
        """Return ranked records with honest match and family signals.

        Multi-token queries require phrase/all-token evidence for a strong hit.
        If none exists, only candidates sharing a meaningful token *and* a
        relevant domain prior are returned as ``related``.  This intentionally
        leaves a query empty rather than promoting an unrelated one-token
        collision such as ``agricultural drone`` -> ``counter-UAS``.
        """

        domain_code = self.resolve_domain(domain)
        if domain is not None and domain_code is None:
            return []
        kind_value = str(kind).upper() if kind else None
        status_value = _status(status) if status else None
        normalized_query = normalize_text(query)
        query_units = set(_semantic_units(query))
        # Numeric quantities and short objective glue are not retrieval keys;
        # they still remain in the public query string and explanation signals.
        query_units = {unit for unit in query_units if not unit.isdigit() and (unit.startswith("@") or len(unit) > 2)}
        query_tokens = {_stem_search_token(token) for token in _tokens(query) if not token.isdigit() and len(token) > 2}
        hints = _domain_hints(query)
        if domain_code:
            hints = {domain_code}

        candidate: set[str] = set()
        if normalized_query:
            candidate.update(self.alias_index.get(normalized_query, ()))
            for family_key in self.family_alias_index.get(normalized_query, ()):
                candidate.update(self.family_members.get(family_key, ()))
            for unit in query_units:
                candidate.update(self.search_term_index.get(unit, ()))
            # A light, bounded typo path: only literal words of four or more
            # characters can fuzzy-match, and the penalty keeps fuzzy hits
            # below a phrase/all-token match.
            available_terms = tuple(self.search_term_index)
            for token in query_tokens:
                if len(token) < 4 or token in self.search_term_index:
                    continue
                for term in available_terms:
                    if term.startswith("@") or len(term) < 4:
                        continue
                    if _edit_distance_one(token, term):
                        candidate.update(self.search_term_index.get(term, ()))
        else:
            candidate = set(self.by_id)

        if domain_code:
            candidate &= set(self.domain_index.get(domain_code, ()))
        if kind_value:
            candidate &= set(self.kind_index.get(kind_value, ()))
        if status_value:
            candidate &= set(self.status_index.get(status_value, ()))
        if not candidate:
            return []

        prefer_direct = any(not self.by_id[record_id]["is_reference_only"] for record_id in candidate)
        scored: list[dict[str, Any]] = []
        for record_id in sorted(candidate):
            record = self.by_id[record_id]
            field_terms = self.search_field_term_sets.get(record_id, {})
            name_terms = self.search_name_term_sets.get(record_id, self.search_token_sets.get(record_id, frozenset()))
            all_terms = self.search_token_sets.get(record_id, frozenset())
            matched_units = query_units.intersection(all_terms)
            name_matched_units = query_units.intersection(name_terms)
            full_name = bool(query_units) and query_units.issubset(name_terms)
            full_record = bool(query_units) and query_units.issubset(all_terms)
            exact_field = any(normalized_query and normalized_query == normalize_text(field) for field in self.search_fields.get(record_id, ()))
            phrase_field = any(normalized_query and normalized_query in normalize_text(field) for field in self.search_fields.get(record_id, ()))
            fuzzy_tokens = [
                token for token in query_tokens
                if token not in all_terms and any(_edit_distance_one(token, term) for term in all_terms if not term.startswith("@") and len(term) >= 4)
            ]
            matched_on: list[str] = []
            for field_name, terms in field_terms.items():
                if query_units.intersection(terms):
                    matched_on.append(field_name)
            matched_on.extend(_semantic_group_labels(matched_units))
            matched_on = list(dict.fromkeys(sorted(matched_on)))
            domain_match = bool(hints and str(record.get("domain_code")) in hints)
            direct_bonus = 250 if prefer_direct and not record["is_reference_only"] else 0
            kind_bonus = {"PRODUCT": 55, "EQUIPMENT": 45, "MATERIAL": 35, "PROCESS": 25, "CAPABILITY": 15}.get(record.get("kind"), 0)
            family_rep_bonus = 15 if self.family_representatives.get(record.get("family_key")) == record_id else 0
            coverage = len(matched_units) / max(1, len(query_units))
            if not query_units:
                match_type = "browse"
                base_score = 100
            elif exact_field:
                match_type = "exact"
                base_score = 10_000
            elif phrase_field and full_name:
                match_type = "phrase"
                base_score = 9_200
            elif full_name:
                match_type = "all_tokens"
                base_score = 8_400
            elif full_record and name_matched_units:
                match_type = "all_tokens"
                base_score = 7_400
            elif full_record and domain_match:
                # A query found in explanatory/uses text is useful context,
                # but it is not a product-name match.  Keep it visibly below
                # phrase/all-token matches and expose the related signal.
                match_type = "related"
                base_score = 1_850
            elif len(query_units) == 1 and matched_units:
                match_type = "alias" if any(unit.startswith("@") for unit in matched_units) else "partial"
                base_score = 4_900
            elif matched_units and domain_match:
                match_type = "related"
                base_score = 2_000
            else:
                # A candidate sharing only an unqualified word is not a useful
                # search hit and is filtered below.
                match_type = "irrelevant"
                base_score = 0
            if fuzzy_tokens and match_type in {"alias", "partial", "related", "irrelevant"}:
                match_type = "fuzzy"
                base_score = max(base_score, 2_500)
            score = int(
                base_score
                + round(coverage * 1_000)
                + (700 if domain_match else (-350 if hints and match_type in {"related", "partial", "fuzzy"} else 0))
                + len(name_matched_units) * 80
                + direct_bonus
                + kind_bonus
                + family_rep_bonus
                - len(fuzzy_tokens) * 300
            )
            scored.append(
                {
                    "record": record,
                    "score": score,
                    "match_type": match_type,
                    "matched_on": matched_on,
                    "matched_units": sorted(matched_units),
                    "domain_match": domain_match,
                    "coverage": coverage,
                    "fuzzy_tokens": fuzzy_tokens,
                }
            )

        strong_types = {"exact", "phrase", "all_tokens", "alias", "browse"}
        strong = [hit for hit in scored if hit["match_type"] in strong_types]
        if query_units and not strong:
            # Related fallback requires domain context.  It is deliberately
            # narrower than token union and carries a visibly weaker signal.
            strong = [hit for hit in scored if hit["match_type"] in {"related", "fuzzy"}]
        elif query_units:
            strong = [hit for hit in scored if hit["match_type"] in strong_types]
            # A shared bridge may have an exact alias while the best honest
            # answer is a domain-matched related family (robotic welding cell
            # -> industrial robotics).  Preserve that fallback candidate so
            # the domain gate below can prefer it over the shared bridge.
            if not any(
                hit["domain_match"] and not hit["record"].get("is_reference_only", False)
                for hit in strong
            ):
                strong.extend(
                    hit for hit in scored
                    if hit["match_type"] == "related"
                    and hit["domain_match"]
                    and not hit["record"].get("is_reference_only", False)
                )
        if not strong:
            return []

        # When the vocabulary provides a domain prior, a matching direct
        # family is more useful than an exact shared/reference bridge from a
        # different domain.  This keeps common primitives navigable while
        # preventing a shared alias from outranking the user's industrial
        # context (for example, robotic welding cell -> machine robotics).
        exact_direct = any(
            hit["match_type"] == "exact" and not hit["record"].get("is_reference_only", False)
            for hit in strong
        )
        if hints and not exact_direct:
            domain_direct = [
                hit for hit in strong
                if hit["domain_match"] and not hit["record"].get("is_reference_only", False)
            ]
            if domain_direct:
                strong = domain_direct

        strong.sort(
            key=lambda hit: (
                -int(hit["score"]),
                str(hit["record"].get("family_key", "")),
                str(hit["record"].get("id", "")),
            )
        )
        if include_variants:
            selected = strong[: max(1, int(limit))]
        else:
            selected = []
            seen_families: set[str] = set()
            for hit in strong:
                family_key = str(hit["record"].get("family_key") or hit["record"].get("id"))
                if family_key in seen_families:
                    continue
                seen_families.add(family_key)
                selected.append(hit)
                if len(selected) >= max(1, int(limit)):
                    break
        return [
            {
                **hit,
                "id": hit["record"]["id"],
                "family_key": hit["record"].get("family_key") or hit["record"]["id"],
                "match_type": hit["match_type"],
                "matched_on": list(hit["matched_on"]),
            }
            for hit in selected
        ]

    def search(
        self,
        query: str = "",
        *,
        domain: str | None = None,
        kind: str | None = None,
        status: str | None = None,
        limit: int = 25,
        include_variants: bool = False,
    ) -> list[dict[str, Any]]:
        """Return JSON-ready records; use :meth:`ranked_search` for scores."""

        return [
            dict(record)
            for record, _score in self.ranked_search(
                query,
                domain=domain,
                kind=kind,
                status=status,
                limit=limit,
                include_variants=include_variants,
            )
        ]

    def integrity(self) -> dict[str, Any]:
        errors: list[str] = []
        ids = [record["id"] for record in self.records]
        if len(ids) != len(set(ids)):
            errors.append("duplicate record id")
        aliases: dict[str, str] = {}
        for record in self.records:
            for alias in record["aliases"]:
                key = normalize_text(alias)
                owner = aliases.get(key)
                if owner and owner != record["id"]:
                    errors.append(f"duplicate alias {alias!r}: {owner} and {record['id']}")
                aliases[key] = record["id"]
            if record["kind"] not in KINDS:
                errors.append(f"{record['id']}: invalid kind")
            if record["status"] not in STATUSES:
                errors.append(f"{record['id']}: invalid status")
            if record["status_epistemic_class"] not in EPISTEMIC_CLASSES:
                errors.append(f"{record['id']}: invalid epistemic class")
            if set(record["dependencies"]) != set(DEP_GROUPS):
                errors.append(f"{record['id']}: invalid dependency groups")
            if record["kind"] == "PRODUCT" and not record["is_reference_only"] and record["domain_code"] != "shared":
                if len(record["dependency_ids"]) < 5:
                    errors.append(f"{record['id']}: product has fewer than five dependencies")
                if len(record["making_ladder"]) < 5:
                    errors.append(f"{record['id']}: product ladder is too short")
            for group in DEP_GROUPS:
                for reference in record["dependencies"][group]:
                    if reference not in self.by_id:
                        errors.append(f"{record['id']}: unresolved dependency {reference}")
            for reference in (*record["upstream"], *record["downstream"], *record["related"]):
                if reference not in self.by_id:
                    errors.append(f"{record['id']}: unresolved link {reference}")
            if not record["is_reference_only"] and not (record["upstream"] or record["downstream"] or record["related"]):
                errors.append(f"{record['id']}: dead-end record")
        return {
            "ok": not errors,
            "record_count": len(self.records),
            "direct_record_count": self.direct_record_count,
            "reference_record_count": self.reference_record_count,
            "domain_counts": self.domain_counts,
            "kind_counts": self.kind_counts,
            "status_counts": self.status_counts,
            "unique_ids": len(set(ids)),
            "unique_aliases": len(aliases),
            "errors": errors,
        }


def _build_catalog() -> IndiaCatalog:
    direct = _direct_rows()
    direct_ids = {record["id"] for record in direct}
    bridges: dict[str, dict[str, Any]] = {}
    for record in direct:
        references = [
            *record["dependency_ids"],
            *record["upstream"],
            *record["downstream"],
            *record["related"],
        ]
        for reference in references:
            if reference not in direct_ids and reference not in bridges:
                bridges[reference] = _stub_record(reference)

    all_records = direct + [bridges[key] for key in sorted(bridges)]
    # Reverse edges make a bridge node useful from the graph endpoint and
    # expose the ``unlocks`` view without changing source-pack assertions.
    reverse_downstream: dict[str, set[str]] = defaultdict(set)
    reverse_related: dict[str, set[str]] = defaultdict(set)
    for record in all_records:
        for reference in (*record["dependency_ids"], *record["upstream"]):
            reverse_downstream[reference].add(record["id"])
        # Reference bridges are often named only in a dependency/downstream
        # edge.  A bounded reverse-related link gives those primitives a
        # deterministic navigation parent without claiming a new capability.
        for reference in (
            *record["dependency_ids"],
            *record["upstream"],
            *record["downstream"],
            *record["related"],
        ):
            if reference not in direct_ids:
                reverse_related[reference].add(record["id"])
    for record in all_records:
        record["downstream"] = sorted(set(record["downstream"]) | reverse_downstream.get(record["id"], set()))
        record["related"] = sorted(set(record["related"]) | reverse_related.get(record["id"], set()))

    # The graph is now closed over direct rows and reference bridges, so the
    # shared quality ladder can inspect dependency status without guessing.
    # Apply the display/family contract before constructing any search index.
    by_id = {record["id"]: record for record in all_records}
    for record in all_records:
        if record.get("status") in {"STRONG", "MISSING"} and record.get("status_epistemic_class") == "ASSUMPTION":
            record.update(_quality_correct_epistemic_status(record))
        # The 05--12 source packs already emit these normalized fields.  Reuse
        # them instead of re-running the same regex-heavy presentation pass on
        # thousands of records during every cold start.
        record["family_key"] = record.get("family_key") or _quality_family_key(record)
        record["variant_label"] = record.get("variant_label") or _quality_variant_label(record)
        record["display_name"] = record.get("display_name") or _quality_display_name(record)
        record["family_label"] = record.get("family_label") or _family_label(record)
        record["making_ladder"] = _quality_making_ladder(record, by_id)

    # Keep the source aliases available to search while making the public
    # aliases globally unique for registry integrity.  A repeated family alias
    # is suffixed only on the later records; token search still finds every
    # variant because its raw alias is indexed below.
    alias_owner: dict[str, str] = {}
    search_fields: dict[str, tuple[str, ...]] = {}
    normalized_fields_build: dict[str, tuple[str, ...]] = {}
    search_token_sets_build: dict[str, frozenset[str]] = {}
    search_term_index_build: dict[str, set[str]] = defaultdict(set)
    search_name_term_sets_build: dict[str, frozenset[str]] = {}
    search_field_term_sets_build: dict[str, dict[str, frozenset[str]]] = {}
    family_members_build: dict[str, list[str]] = defaultdict(list)
    family_alias_index_build: dict[str, set[str]] = defaultdict(set)
    alias_index_build: dict[str, set[str]] = defaultdict(set)
    token_index_build: dict[str, set[str]] = defaultdict(set)
    for record in all_records:
        public_aliases: list[str] = []
        raw_aliases = tuple(record.pop("_search_aliases", ()))
        for alias in record["aliases"]:
            norm = normalize_text(alias)
            if not norm:
                continue
            owner = alias_owner.get(norm)
            public_alias = alias
            if owner and owner != record["id"]:
                public_alias = f"{alias} [{record['id']}]"
                norm = normalize_text(public_alias)
            if norm not in alias_owner:
                alias_owner[norm] = record["id"]
                public_aliases.append(public_alias)
        if not public_aliases:
            public_aliases = [record["id"]]
            alias_owner.setdefault(normalize_text(record["id"]), record["id"])
        record["aliases"] = public_aliases
        field_values = tuple(
            dict.fromkeys(
                (
                    record["id"],
                    record["canonical_name"],
                    *raw_aliases,
                    *public_aliases,
                    record.get("family_label", ""),
                    record["category"],
                    record.get("explanation", ""),
                    *record["uses"],
                )
            )
        )
        search_fields[record["id"]] = field_values
        normalized_values = tuple(normalize_text(field) for field in field_values)
        normalized_fields_build[record["id"]] = normalized_values
        field_term_sets = {
            "name": frozenset(_semantic_units(" ".join((record["canonical_name"], record.get("family_label", ""))))),
            "aliases": frozenset(_semantic_units(" ".join((*raw_aliases, *public_aliases)))),
            "category": frozenset(_semantic_units(record["category"])),
            "explanation": frozenset(_semantic_units(record.get("explanation", ""))),
            "uses": frozenset(_semantic_units(" ".join(record["uses"]))),
        }
        search_field_term_sets_build[record["id"]] = field_term_sets
        name_terms = frozenset(set(field_term_sets["name"]) | set(field_term_sets["aliases"]))
        all_terms = frozenset(set().union(*(set(values) for values in field_term_sets.values())))
        search_name_term_sets_build[record["id"]] = name_terms
        search_token_sets_build[record["id"]] = all_terms
        for term in all_terms:
            search_term_index_build[term].add(record["id"])
        family_key = str(record.get("family_key") or _quality_family_key(record["id"]))
        record["family_key"] = family_key
        record["family_label"] = str(record.get("family_label") or _family_label(record))
        family_members_build[family_key].append(record["id"])
        for alias in (*raw_aliases, *public_aliases, record["canonical_name"], record.get("family_label", "")):
            normalized_alias = normalize_text(alias)
            if normalized_alias:
                family_alias_index_build[normalized_alias].add(family_key)
        for field in field_values:
            normalized = normalize_text(field)
            if normalized:
                alias_index_build[normalized].add(record["id"])
            for token in _tokens(field):
                token_index_build[token].add(record["id"])

    domain_index_build: dict[str, set[str]] = defaultdict(set)
    kind_index_build: dict[str, set[str]] = defaultdict(set)
    status_index_build: dict[str, set[str]] = defaultdict(set)
    for record in all_records:
        domain_index_build[record["domain_code"]].add(record["id"])
        kind_index_build[record["kind"]].add(record["id"])
        status_index_build[record["status"]].add(record["id"])

    domain_aliases: dict[str, str] = {"shared": "shared"}
    for code, meta in DOMAIN_META.items():
        for value in (code, str(int(code)), meta["key"], meta["name"]):
            domain_aliases[normalize_text(value).replace(" ", "_")] = code

    catalog = IndiaCatalog(
        records=tuple(sorted(all_records, key=lambda record: record["id"])),
        by_id=by_id,
        token_index={key: tuple(sorted(value)) for key, value in token_index_build.items()},
        alias_index={key: tuple(sorted(value)) for key, value in alias_index_build.items()},
        domain_index={key: tuple(sorted(value)) for key, value in domain_index_build.items()},
        kind_index={key: tuple(sorted(value)) for key, value in kind_index_build.items()},
        status_index={key: tuple(sorted(value)) for key, value in status_index_build.items()},
        domain_aliases=domain_aliases,
        search_fields=search_fields,
        normalized_fields=normalized_fields_build,
        search_token_sets=search_token_sets_build,
        direct_record_count=len(direct),
        search_term_index={key: tuple(sorted(value)) for key, value in search_term_index_build.items()},
        search_name_term_sets=search_name_term_sets_build,
        search_field_term_sets=search_field_term_sets_build,
        family_members={key: tuple(sorted(value)) for key, value in family_members_build.items()},
        family_representatives={
            key: min(values, key=lambda record_id: _family_representative_rank(by_id[record_id]))
            for key, values in family_members_build.items()
        },
        family_alias_index={key: tuple(sorted(value)) for key, value in family_alias_index_build.items()},
    )
    report = catalog.integrity()
    if not report["ok"]:
        raise ValueError("India V1 catalog integrity failed: " + "; ".join(report["errors"][:12]))
    return catalog


_CATALOG_CACHE: IndiaCatalog | None = None
_CATALOG_CACHE_LOCK = Lock()


def get_catalog() -> IndiaCatalog:
    """Build the combined catalog once, with a single-flight cold start."""

    global _CATALOG_CACHE
    cached = _CATALOG_CACHE
    if cached is not None:
        return cached
    with _CATALOG_CACHE_LOCK:
        # The second check is the important part: concurrent callers waiting
        # on the first build reuse its result instead of rebuilding 14k rows.
        if _CATALOG_CACHE is None:
            _CATALOG_CACHE = _build_catalog()
        return _CATALOG_CACHE


def clear_catalog_cache() -> None:
    """Test/dev hook; production API callers should use the cached catalog."""

    global _CATALOG_CACHE
    with _CATALOG_CACHE_LOCK:
        _CATALOG_CACHE = None


def summary(catalog: IndiaCatalog | None = None) -> dict[str, Any]:
    catalog = catalog or get_catalog()
    direct = [record for record in catalog.records if not record["is_reference_only"]]
    owned = [record for record in direct if record["domain_code"] != "shared"]
    return {
        "depth_profile": DEPTH_PROFILE,
        "record_count": len(catalog.records),
        "direct_record_count": catalog.direct_record_count,
        "owned_record_count": len(owned),
        "shared_source_record_count": len(direct) - len(owned),
        "reference_record_count": catalog.reference_record_count,
        "domain_count": len(DOMAIN_ORDER),
        "domain_counts": catalog.domain_counts,
        "kind_counts": catalog.kind_counts,
        "status_counts": catalog.status_counts,
        "status_epistemic_counts": catalog.epistemic_counts,
        "direct_kind_counts": dict(sorted(Counter(record["kind"] for record in direct).items())),
        "direct_status_counts": dict(sorted(Counter(record["status"] for record in direct).items())),
        "direct_status_epistemic_counts": dict(sorted(Counter(record["status_epistemic_class"] for record in direct).items())),
        "all_record_kind_counts": catalog.kind_counts,
        "all_record_status_counts": catalog.status_counts,
        "all_record_status_epistemic_counts": catalog.epistemic_counts,
        "integrity": {
            "unique_ids": len(catalog.by_id),
            "unique_aliases": sum(len(record["aliases"]) for record in catalog.records),
            "all_references_resolve": True,
        },
    }


def domains(catalog: IndiaCatalog | None = None) -> list[dict[str, Any]]:
    catalog = catalog or get_catalog()
    rows: list[dict[str, Any]] = []
    for code in DOMAIN_ORDER:
        owned = [record for record in catalog.records if not record["is_reference_only"] and record["domain_code"] == code]
        rows.append(
            {
                "id": code,
                "code": code,
                "key": DOMAIN_META[code]["key"],
                "name": DOMAIN_META[code]["name"],
                "description": f"Broad V1 ontology coverage for {DOMAIN_META[code]['name']}; status overlays are not qualified supply or effective capacity claims.",
                "record_count": len(owned),
                "kind_counts": dict(sorted(Counter(record["kind"] for record in owned).items())),
                "status_counts": dict(sorted(Counter(record["status"] for record in owned).items())),
                "depth_profile": DEPTH_PROFILE,
            }
        )
    return rows


__all__ = [
    "DEPTH_PROFILE",
    "DEP_GROUPS",
    "DOMAIN_META",
    "DOMAIN_ORDER",
    "EPISTEMIC_CLASSES",
    "IndiaCatalog",
    "KINDS",
    "STATUSES",
    "clear_catalog_cache",
    "domains",
    "get_catalog",
    "normalize_text",
    "summary",
]
