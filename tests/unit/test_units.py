import numpy as np
import numpy.testing as npt
import pytest
from scmdata.testing import get_single_ts

from local.h2_adjust.units import (
    _get_unit_scaling,
    sanitize_combustion_intensity_units,
    sanitize_production_intensity_units,
)


@pytest.mark.parametrize(
    "source,target,exp",
    [
        ("kg NOx / MWh", "kg NOx / MWh", 1),
        ("kg NOx / MWh", "t NOx / MWh", 1 / 1000),
        ("g NOx/kWh", "kg NOx / MWh", 1),
        ("kg NOx/TJ", "kg NOx / MWh", 3600 / 1e6),
        ("kg /t", "kg / kg", 1 / 1000),
    ],
)
def test_unit_scaling(source, target, exp):
    np.testing.assert_almost_equal(_get_unit_scaling(source, target), exp)


@pytest.mark.parametrize(
    "unit,product,exp",
    (
        ("kg NOx/TJ", "NOx", 3600 / 1e6),
        ("kg NOx / MWh", "NOx", 1),
        ("g CH4/MJ", "CH4", 3600 / 1e3),
    ),
)
def test_convert_combustion_intensities(unit, product, exp):
    inp = get_single_ts(
        data=[1],
        index=[2000],
        variable="Emissions Intensity",
        unit=unit,
        product=product,
    )
    res = sanitize_combustion_intensity_units(inp)

    product_unit = "H" if product == "H2" else product
    assert res.get_unique_meta("unit", True) == f"kg {product_unit} / MWh"
    npt.assert_almost_equal(res.values, exp)


@pytest.mark.parametrize(
    "unit,carrier,product,exp",
    (
        ("% of H2", "H2", "H2", 0.01),
        ("kgNOx/tNH3", "NH3", "NOx", 1 / 1000 * (14 + 3) / 3),
        ("kgNH3/tNH3", "NH3", "NH3", 1 / 1000 * (14 + 3) / 3),
        ("% H2 component of fuel", "NH3", "H2", 0.01),
        ("% H2 component of fuel", "CH4", "H2", 0.01),
        ("% of fuel (LNG) consumption", "CH4", "CH4", 0.01 * (12 + 4) / 4 / 2),
        ("% NH3 used", "NH3", "NH3", 0.01 * (14 + 3) / 3),
    ),
)
def test_convert_production_intensities(unit, carrier, product, exp):
    inp = get_single_ts(
        data=[1],
        index=[2000],
        variable="Emissions Intensity",
        unit=unit,
        carrier=carrier,
        product=product,
    )
    res = sanitize_production_intensity_units(inp)

    product_unit = "H" if product == "H2" else product
    assert res.get_unique_meta("unit", True) == f"kg {product_unit} / kg H"
    npt.assert_almost_equal(res.values, exp)
