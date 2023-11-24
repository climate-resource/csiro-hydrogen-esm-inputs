import numpy as np
import pytest

from local.h2_adjust.units import _get_unit_scaling


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
def test_convert_intensities(source, target, exp):
    np.testing.assert_almost_equal(_get_unit_scaling(source, target), exp)
