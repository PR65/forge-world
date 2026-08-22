from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class BaseDim(Enum):
    ORE = "ore_t"
    METAL = "metal_t"
    OXIDE = "oxide_t"
    ALLOY = "alloy_t"
    PRODUCT = "product_t"
    ENERGY = "Wh"
    TIME = "h"
    COUNT = "pcs"
    CURRENCY = "USD"
    AREA = "m2"
    VOLUME = "m3"


_MASS_FAMILIES = ("ore", "metal", "oxide", "alloy", "product")
_SINGLE: Dict[str, Dim] = {}


class Dim:
    """Dimensional vector over base dimensions. Immutable, hashable."""

    __slots__ = ("exp",)

    def __init__(self, exp: Optional[Dict[str, int]] = None):
        object.__setattr__(
            self, "exp", tuple(sorted((k, v) for k, v in (exp or {}).items() if v != 0))
        )

    @property
    def exp_dict(self) -> Dict[str, int]:
        return dict(self.exp)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dim) and self.exp == other.exp

    def __hash__(self) -> int:
        return hash(self.exp)

    def __mul__(self, other: "Dim") -> "Dim":
        e = self.exp_dict
        for k, v in other.exp_dict.items():
            e[k] = e.get(k, 0) + v
        return Dim(e)

    def __truediv__(self, other: "Dim") -> "Dim":
        e = self.exp_dict
        for k, v in other.exp_dict.items():
            e[k] = e.get(k, 0) - v
        return Dim(e)

    def __pow__(self, n: int) -> "Dim":
        return Dim({k: v * n for k, v in self.exp_dict.items()})

    def is_dimensionless(self) -> bool:
        return not self.exp

    def __str__(self) -> str:
        if not self.exp:
            return "1"
        num, den = [], []
        for k, v in self.exp:
            (num if v > 0 else den).append(f"{k}^{abs(v)}" if abs(v) != 1 else k)
        s = "*".join(num) if num else "1"
        if den:
            s += "/" + "*".join(den)
        return s


DIMLESS = Dim()
for d in BaseDim:
    _SINGLE[d.value] = Dim({d.value: 1})
POWER_DIM = Dim({"Wh": 1, "h": -1})


def mass_dim(family: str) -> Dim:
    if family not in _MASS_FAMILIES:
        raise KeyError(f"unknown mass family '{family}'")
    return _SINGLE[f"{family}_t"]


UNITS: Dict[str, tuple] = {}


def _reg(name: str, dim: Dim, factor: float):
    UNITS[name] = (dim, factor)


for fam in _MASS_FAMILIES:
    _reg(f"g_{fam}", _SINGLE[f"{fam}_t"], 1e-6)
    _reg(f"kg_{fam}", _SINGLE[f"{fam}_t"], 1e-3)
    _reg(f"t_{fam}", _SINGLE[f"{fam}_t"], 1.0)
    _reg(f"kt_{fam}", _SINGLE[f"{fam}_t"], 1e3)
    _reg(f"Mt_{fam}", _SINGLE[f"{fam}_t"], 1e6)

for u, f in (("J", 1 / 3600), ("kJ", 1 / 3.6), ("MJ", 1 / 0.0036), ("GJ", 1 / 3.6e-6),
             ("Wh", 1.0), ("kWh", 1e3), ("MWh", 1e6), ("GWh", 1e9), ("TWh", 1e12)):
    _reg(u, _SINGLE["Wh"], f)

_reg("W", POWER_DIM, 1.0)
_reg("kW", POWER_DIM, 1e3)
_reg("MW", POWER_DIM, 1e6)
_reg("GW", POWER_DIM, 1e9)

_TIME_DIM = _SINGLE["h"]
for u, f in (("s", 1 / 3600), ("min", 1 / 60), ("h", 1.0), ("d", 24.0), ("wk", 168.0),
             ("mo", 8760.0 / 12.0), ("yr", 8760.0)):
    _reg(u, _TIME_DIM, f)

_COUNT_UNITS = (
    "pcs", "units", "robots", "actuators", "reducers", "motors", "cells", "batteries",
    "wafers", "panels", "modules", "satellites", "jobs", "lines", "machines", "vehicles",
    "inverters", "strings", "encoders", "bearings", "harnesses",
)
for u in _COUNT_UNITS:
    _reg(u, _SINGLE["pcs"], 1.0)
_reg("%", _SINGLE["pcs"], 1.0)

_reg("USD", _SINGLE["USD"], 1.0)
# Currencies share the USD *value* dimension for arithmetic but carry distinct
# currency identities: cross-currency operations without an explicit FX context are
# rejected at the arithmetic level too (V0 leak: EUR*pcs/pcs silently became USD).
_CURRENCIES = ("USD", "EUR", "INR")
for _c in _CURRENCIES:
    _reg(_c, _SINGLE["USD"], 1.0)
CURRENCY_OF_UNIT: Dict[str, str] = {u: u for u in _CURRENCIES}

_reg("m2", _SINGLE["m2"], 1.0)
_reg("km2", _SINGLE["m2"], 1e6)
_reg("m3", _SINGLE["m3"], 1.0)
_reg("L", _SINGLE["m3"], 1e-3)


def parse_dim(spec: str) -> Dim:
    spec = spec.strip()

    def parse_side(side: str) -> Dim:
        d = DIMLESS
        for part in side.split("*"):
            part = part.strip()
            if not part:
                continue
            if "^" in part:
                base, pw = part.split("^")
                d = d * (_SINGLE[base.strip()] ** int(pw))
            else:
                d = d * _SINGLE[part]
        return d

    if not spec or spec == "1":
        return DIMLESS
    num, _, den = spec.partition("/")
    d = parse_side(num)
    if den.strip():
        d = d / parse_side(den)
    return d


_PREFIXES = {"k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "m": 1e-3}


def _resolve_token(tok: str):
    if tok in UNITS:
        return UNITS[tok]
    if len(tok) > 1:
        for p, mult in _PREFIXES.items():
            if tok.startswith(p) and tok[1:] in UNITS:
                d, f = UNITS[tok[1:]]
                return (d, f * mult)
    return None


def ensure_unit(name: str) -> bool:
    """Parse composite unit strings like 'pcs/yr', 'kg_product/yr', 'MUSD'.

    Registers and returns True on success; False if not interpretable.
    """
    if name in UNITS:
        return True
    name = name.strip()
    if not name:
        return False
    try:
        num_str, _, den_str = name.partition("/")
        dim = DIMLESS
        factor = 1.0
        for side, sign in ((num_str, 1), (den_str, -1)):
            side = side.strip()
            if not side or side == "1":
                continue
            for tok in side.split("*"):
                tok = tok.strip()
                r = _resolve_token(tok)
                if r is None:
                    d2 = None
                    try:
                        d2 = parse_dim(tok)
                    except Exception:
                        d2 = None
                    if d2 is None:
                        return False
                    dim = dim * d2 if sign > 0 else dim / d2
                else:
                    d, f = r
                    if sign > 0:
                        dim = dim * d
                        factor *= f
                    else:
                        dim = dim / d
                        factor /= f
        _reg(name, dim, factor)
        return True
    except Exception:
        return False


class UnitError(Exception):
    pass


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str

    def __post_init__(self):
        if self.unit not in UNITS:
            ok = ensure_unit(self.unit) if isinstance(self.unit, str) else False
            if not ok:
                raise UnitError(f"unknown unit '{self.unit}'")

    @property
    def dim(self) -> Dim:
        return UNITS[self.unit][0]

    @property
    def factor(self) -> float:
        return UNITS[self.unit][1]

    def canonical(self) -> float:
        return self.value * self.factor

    def to(self, target: str) -> "Quantity":
        tdim, tfac = UNITS[target]
        if tdim != self.dim:
            raise UnitError(
                f"incompatible dimensions: {self.unit} ({self.dim}) -> {target} ({tdim})"
            )
        return Quantity(self.canonical() / tfac, target)

    def check_same_dim(self, other: "Quantity"):
        if self.dim != other.dim:
            raise UnitError(f"dimension mismatch: {self.unit} vs {other.unit}")

    def __add__(self, other: "Quantity") -> "Quantity":
        self.check_same_dim(other)
        return Quantity(self.value + other.to(self.unit).value, self.unit)

    def __sub__(self, other: "Quantity") -> "Quantity":
        self.check_same_dim(other)
        return Quantity(self.value - other.to(self.unit).value, self.unit)

    def __mul__(self, other):
        if isinstance(other, Quantity):
            new_dim = self.dim * other.dim
            raw = self.canonical() * other.canonical()
            return _check_currency_pair(self, other, from_canonical(raw, new_dim))
        if isinstance(other, (int, float)):
            return Quantity(self.value * other, self.unit)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Quantity):
            new_dim = self.dim / other.dim
            raw = self.canonical() / other.canonical()
            return _check_currency_pair(self, other, from_canonical(raw, new_dim))
        if isinstance(other, (int, float)):
            return Quantity(self.value / other, self.unit)
        return NotImplemented

    def __neg__(self):
        return Quantity(-self.value, self.unit)

    def __lt__(self, other):
        self.check_same_dim(other)
        return self.canonical() < other.canonical()

    def __le__(self, other):
        self.check_same_dim(other)
        return self.canonical() <= other.canonical()

    def __gt__(self, other):
        self.check_same_dim(other)
        return self.canonical() > other.canonical()

    def __ge__(self, other):
        self.check_same_dim(other)
        return self.canonical() >= other.canonical()

    def isclose(self, other: "Quantity", rel: float = 1e-9, abs_tol: float = 0.0) -> bool:
        self.check_same_dim(other)
        return math.isclose(self.canonical(), other.canonical(), rel_tol=rel, abs_tol=abs_tol)

    def __str__(self):
        v = self.value
        if abs(v - round(v)) < 1e-12 and abs(v) < 1e15:
            return f"{int(round(v))} {self.unit}"
        return f"{v:.6g} {self.unit}"


_DISPLAY_UNIT: Dict[str, tuple] = {
    "ore_t": ("t_ore", 1.0), "metal_t": ("t_metal", 1.0), "oxide_t": ("t_oxide", 1.0),
    "alloy_t": ("t_alloy", 1.0), "product_t": ("t_product", 1.0), "Wh": ("MWh", 1e6),
    "h": ("h", 1.0), "pcs": ("pcs", 1.0), "USD": ("USD", 1.0), "m2": ("m2", 1.0),
    "m3": ("m3", 1.0),
}
_POWER_DISPLAY = ("kW", 1e3)


def from_canonical(raw: float, dim: Dim) -> Quantity:
    if dim.is_dimensionless():
        return Quantity(raw, "pcs")
    exp = dim.exp_dict
    if len(exp) == 1:
        base, power = next(iter(exp.items()))
        if power == 1 and base in _DISPLAY_UNIT:
            u, f = _DISPLAY_UNIT[base]
            return Quantity(raw / f, u)
    if exp == {"Wh": 1, "h": -1}:
        return Quantity(raw / _POWER_DISPLAY[1], _POWER_DISPLAY[0])
    unit_str, factor = _composite_display(dim)
    return Quantity(raw / factor, unit_str)


_COMPOSITE_PREF = {
    "USD": ("USD", 1.0), "pcs": ("pcs", 1.0), "h": ("yr", 8760.0),
    "Wh": ("MWh", 1e6), "ore_t": ("t_ore", 1.0), "metal_t": ("t_metal", 1.0),
    "oxide_t": ("t_oxide", 1.0), "alloy_t": ("t_alloy", 1.0),
    "product_t": ("t_product", 1.0), "m2": ("m2", 1.0), "m3": ("m3", 1.0),
}


def _composite_display(dim: Dim):
    exp = dim.exp_dict
    num_units, den_units, factor = [], [], 1.0
    for base, power in sorted(exp.items()):
        u, f = _COMPOSITE_PREF.get(base, (base, 1.0))
        if power > 0:
            num_units.append(u if power == 1 else f"{u}^{power}")
            factor *= f ** power
        else:
            den_units.append(u if power == -1 else f"{u}^{-power}")
            factor /= f ** (-power)
    unit_str = "*".join(num_units) if num_units else "1"
    if den_units:
        unit_str += "/" + "*".join(den_units)
    UNITS.setdefault(unit_str, (dim, factor))
    return unit_str, factor


def q(value: float, unit: str) -> Quantity:
    return Quantity(float(value), unit)


def _currency_of_unit(unit: str) -> Optional[str]:
    toks = set()
    for side in unit.split("/"):
        for tok in side.split("*"):
            tok = tok.strip()
            if tok in CURRENCY_OF_UNIT:
                toks.add(tok)
    if len(toks) > 1:
        raise UnitError(f"multiple currencies in one quantity: {sorted(toks)}")
    return next(iter(toks)) if toks else None


def _check_currency_pair(a: "Quantity", b: "Quantity", out: "Quantity") -> "Quantity":
    """Cross-currency arithmetic without an explicit FX context is rejected.

    Distinct currencies meeting in one expression raise UnitError (V0 silently
    normalized EUR -> USD here). Same-currency cancel-outs stay in that currency.
    """
    ca, cb = _currency_of_unit(a.unit), _currency_of_unit(b.unit)
    if ca and cb and ca != cb:
        raise UnitError(
            f"cross-currency arithmetic {ca} vs {cb} requires an explicit scenario "
            f"fx_rate via units.convert(); refusing silent normalization"
        )
    surviving = ca or cb
    if surviving is None or out.unit == surviving:
        return out
    # Display-unit normalization relabeled a currency-bearing result (the value
    # dimension renders as 'USD' by default, e.g. 'USD*pcs'). If exactly one
    # currency entered the expression, restore its identity at face value.
    if surviving and out.dim.exp_dict.get("USD", 0) >= 1:
        return Quantity(out.value, surviving)
    return out


def register_unit(name: str, dim_spec, factor: float):
    d = parse_dim(dim_spec) if isinstance(dim_spec, str) else dim_spec
    _reg(name, d, factor)


def convert(qty: Quantity, target: str, fx_rate: Optional[float] = None) -> Quantity:
    td = UNITS[target][0]
    if qty.unit == target:
        return qty
    if qty.dim == _SINGLE["USD"] and td == _SINGLE["USD"]:
        if fx_rate is None:
            raise UnitError(
                f"currency conversion {qty.unit} -> {target} requires an explicit scenario "
                f"fx_rate (no silent rate assumptions)"
            )
        return Quantity(qty.value * fx_rate, target)
    if qty.dim == td:
        return qty.to(target)
    raise UnitError(
        f"cannot convert {qty.unit} -> {target}; distinct physical dimensions require an "
        f"explicit recipe/assumption factor, not a unit conversion"
    )


YEAR_HOURS = 8760.0


def annual_scalar(qty: Quantity) -> float:
    """Numeric annual amount in canonical base units.

    Per-year rates ('pcs/yr', 't_product/yr') become their plain annual amounts;
    per-hour rates are scaled by 8760; timeless quantities pass through.
    """
    c = qty.canonical()
    e_h = qty.dim.exp_dict.get("h", 0)
    return c * (YEAR_HOURS ** (-e_h))


def annualize(per_hour_rate: float, unit: str) -> Quantity:
    return Quantity(per_hour_rate * YEAR_HOURS, unit)
