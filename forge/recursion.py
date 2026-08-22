from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .evidence import ProofGraph
from .model import EquipmentClass, ProductionRecipe, World


@dataclass
class RecursionEvent:
    equipment_class: str
    triggered_by: List[str]
    expanded: bool
    chain: List[str] = field(default_factory=list)

    def to_json(self) -> Dict:
        return dict(
            equipment_class=self.equipment_class,
            triggered_by=self.triggered_by,
            expanded=self.expanded,
            chain=self.chain,
        )


TRIGGER_CONCENTRATION = 0.7
TRIGGER_LEAD_TIME_MONTHS = 9.0


def strategic_materiality(
    w: World,
    equipment_class_id: str,
    binding: bool,
    import_denial: bool = False,
) -> Tuple[bool, List[str]]:
    """Lazy recursion trigger rules (MODEL_CONTRACT C11)."""
    triggers: List[str] = []
    ent = w.entities.get(equipment_class_id)
    if binding:
        triggers.append("binding constraint (machine-hour limit hit)")
    if import_denial:
        triggers.append("import-denial scenario active")
    if ent is not None:
        countries = list(getattr(ent, "dominant_supplier_countries", ()) or ())
        if len(countries) == 1:
            triggers.append(f"single-country supplier concentration: {countries[0]}")
        dom = getattr(ent, "domestically_producible", None)
        if dom is False:
            triggers.append("flagged not domestically producible")
        lt = getattr(ent, "machine_hours_per_year", None)
    return (len(triggers) > 0, triggers)


def expansion_chain(w: World, equipment_class_id: str) -> List[str]:
    """Return the equipment's own production chain if the pack defines one."""
    chain: List[str] = []
    for e in w.out_edges(equipment_class_id, "recurses_into"):
        chain.append(e.dst)
        chain.extend(expansion_chain(w, e.dst))
    return chain


def expand_recursion(
    w: World,
    pg: ProofGraph,
    equipment_class_id: str,
    binding: bool,
    import_denial: bool = False,
) -> RecursionEvent:
    do, triggers = strategic_materiality(w, equipment_class_id, binding, import_denial)
    chain = expansion_chain(w, equipment_class_id) if do else []
    event = RecursionEvent(
        equipment_class=equipment_class_id,
        triggered_by=triggers,
        expanded=do and bool(chain),
        chain=chain,
    )
    if do:
        pg.derive(
            [],
            f"Lazy recursion into {equipment_class_id}: {', '.join(triggers)}",
            {"chain": chain},
        )
    return event
