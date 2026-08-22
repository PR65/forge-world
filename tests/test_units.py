import math

import pytest

from forge.units import (
    Dim,
    Quantity,
    UnitError,
    annual_scalar,
    convert,
    q,
)


def test_mass_families_not_interconvertible():
    a = q(1, "t_ore")
    b = q(1, "t_metal")
    with pytest.raises(UnitError):
        a + b
    with pytest.raises(UnitError):
        a.to("t_metal")


def test_metric_prefixes_within_family():
    assert q(2, "Mt_ore").to("t_ore").value == 2e6
    assert q(500, "kg_metal").to("t_metal").value == 0.5


def test_energy_time_consistency():
    power = q(5, "MW")
    hours = q(3, "h")
    e = power * hours
    assert e.to("MWh").value == 15
    with pytest.raises(UnitError):
        q(1, "MWh").to("MW")


def test_peak_power_is_not_annual_energy():
    p = q(1.5, "GW")
    e = q(3, "GWh")
    assert p.dim != e.dim


def test_composite_unit_cost_and_rollup():
    unit_cost = q(100, "USD") / q(4, "pcs")
    total = unit_cost * q(1000, "robots")
    assert abs(total.value - 25000) < 1e-9


def test_currency_conversion_requires_explicit_rate():
    with pytest.raises(UnitError):
        convert(q(10, "USD"), "INR")
    out = convert(q(10, "USD"), "INR", fx_rate=83.0)
    assert out.unit == "INR" and abs(out.value - 830) < 1e-9


def test_addition_requires_same_dim():
    with pytest.raises(UnitError):
        q(1, "kWh") + q(1, "pcs")


def test_annual_scalar_per_year_units():
    rate = q(60000, "pcs/yr")
    assert annual_scalar(rate) == 60000
    per_hour = q(60, "pcs/h") if _has("pcs/h") else None
    if per_hour is not None:
        assert annual_scalar(per_hour) == 60 * 8760
    plain = q(42, "pcs")
    assert annual_scalar(plain) == 42


def _has(u):
    from forge.units import UNITS

    try:
        Quantity(1, u)
        return True
    except UnitError:
        return False


def test_unknown_unit_rejected():
    with pytest.raises(UnitError):
        q(1, "florbs")


def test_dimensional_vector_algebra():
    d = Dim({"pcs": 1}) / Dim({"h": 1})
    assert str(d) == "pcs/h"
    assert (Dim({"pcs": 1}) * Dim({"h": -1})) == d


def test_comparison_operators():
    assert q(1, "t_ore") < q(1.5, "t_ore")
    assert q(900, "kg_ore") <= q(1, "t_ore")
    with pytest.raises(UnitError):
        q(1, "kg_ore") < q(1, "kg_metal")


def test_negative_and_scale():
    v = q(3, "MW") * 2
    assert v.value == 6
    assert (-v).value == -6
