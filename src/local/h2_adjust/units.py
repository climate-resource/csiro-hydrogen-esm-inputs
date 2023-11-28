"""
Additional project specific units
"""
from typing import Any

import scmdata
from scmdata.units import UNIT_REGISTRY, UnitConverter

from local.h2_adjust.exceptions import SanitizeError

if not hasattr(UNIT_REGISTRY, "hydrogen"):
    UNIT_REGISTRY.define("H = [hydrogen] = H2")
    UNIT_REGISTRY.define("hydrogen = H")
    UNIT_REGISTRY.define("t{symbol} = t * {symbol}".format(symbol="H"))

__all__ = [
    "UNIT_REGISTRY",
    "sanitize_combustion_intensity_units",
    "sanitize_production_intensity_units",
]


def _get_unit_scaling(source_unit: str | Any, target_unit: str) -> float:
    if not isinstance(source_unit, str):
        return 1.0
    else:
        uc = UnitConverter(source_unit, target_unit)

        return uc.convert_from(1)


def sanitize_combustion_intensity_units(
    intensities: scmdata.ScmRun, energy_unit: str = "MWh", mass_unit: str = "kg"
) -> scmdata.ScmRun:
    """
    Convert emissions intensities to a common set of units

    Default target unit is "kg X / MWh"
    """

    def _convert_intensities(ts: scmdata.ScmRun):
        product: str = ts.get_unique_meta("product", True)
        unit: str = ts.get_unique_meta("unit", True)
        target_unit = f"{mass_unit} {product} / {energy_unit}"

        scale = _get_unit_scaling(unit, target_unit)
        result = ts * scale
        result["unit"] = target_unit
        return result

    return intensities.apply(_convert_intensities)


def h2_mass_factor(unit: str, species: str):
    """
    Calculate a scaling factor to convert 1 kg of H into x kg of `species` 
    
    This assumes that the mass of H is preserved during the conversion. 
    """
    if species == "H2":
        factor = 1
    elif species == "CH4":
        factor = (12 + 4) / 4
    elif species == "NH3":
        factor = (14 + 3) / 3
    elif species == "NOx":
        # Assumes mass equivalence and NO2
        factor = 14 + 2 * 16
    else:
        raise SanitizeError(unit)

    return factor


def sanitize_production_intensity_units(
    intensities: scmdata.ScmRun, mass_unit: str = "kg"
) -> scmdata.ScmRun:
    """
    Convert production emissions intensities and leakage rates to a common set of units

    Default target unit is "kg Product / kg H2"
    """

    def _convert_intensities(ts: scmdata.ScmRun):
        product: str = ts.get_unique_meta("product", True)
        carrier: str = ts.get_unique_meta("carrier", True)
        unit: str = ts.get_unique_meta("unit", True)

        target_unit = (
            f"{mass_unit} {product if product != 'H2' else 'H'} / {mass_unit} H"
        )

        if unit in ["% of H2", "% H2 component of fuel"]:
            assert product == "H2"  # noqa: S101
            scale = 1 / 100
        elif unit in ["%", "% of fuel (LNG) consumption", "% NH3 used"]:
            assert product != "H2"  # noqa: S101
            scale = 1 / 100  # % -> kg H2 / kg H2
            # kg H2 / kg H2 = (kg H2 / kg H2) * (mass_factor * kg X / kg H2) = kg X / kg H2
            mass_factor = h2_mass_factor(unit, carrier)

            # Should be larger (products are all heavier than H)
            assert mass_factor > 1  # noqa: S101
            scale = scale * mass_factor
        elif unit == "kgNH3/tNH3" or unit == "kgNOx/tNH3":
            # kg X / t NH3 = (kg X / t NH3) * (0.001 tNH3 / kg NH3) * (19 kg NH3 / 3 kg H2) = kg X / kg H2
            scale = _get_unit_scaling("kg / t", "kg/kg") * h2_mass_factor(unit, "NH3")

            assert carrier == "NH3"  # noqa: S101
        else:
            raise SanitizeError(unit)

        result = ts * scale
        result["unit"] = target_unit
        return result

    return intensities.apply(_convert_intensities)
