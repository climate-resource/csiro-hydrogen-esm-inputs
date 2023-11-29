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
        raise ValueError(source_unit)  # noqa: TRY004

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

        try:
            scale = _get_unit_scaling(unit, target_unit)
        except ValueError as e:
            raise SanitizeError(unit, target_unit) from e

        result = ts * scale
        result["unit"] = target_unit
        return result

    return intensities.apply(_convert_intensities)


def h2_mass_factor(species: str):
    """
    Calculate a scaling factor to convert 1 kg of H into x kg of `species`

    This assumes that the mass of H is preserved during the conversion.
    """
    if species == "H2":
        # H2 -> 2H
        factor = get_mass_equivalence(
            molar_mass_a=2,
            molar_mass_b=1,
            stoichiometric_coefficient_a=1,
            stoichiometric_coefficient_b=2,
        )
    elif species == "CH4":
        # CO2 + 4H2 -> CH4 + 2H20 (over catalysts)
        factor = get_mass_equivalence(
            molar_mass_a=2,
            molar_mass_b=12 + 4,
            stoichiometric_coefficient_a=4,
            stoichiometric_coefficient_b=1,
        )
    elif species == "NH3":
        # 3H2 + N2 -> 2NH3 (Haber Bosch process)
        factor = get_mass_equivalence(
            molar_mass_a=1,
            molar_mass_b=14 + 3,
            stoichiometric_coefficient_a=3,
            stoichiometric_coefficient_b=1,
        )
    else:
        raise ValueError(species)

    return factor


def get_mass_equivalence(
    molar_mass_a: float,
    molar_mass_b: float,
    stoichiometric_coefficient_a: int,
    stoichiometric_coefficient_b: int,
) -> float:
    """
    Get mass equivalence

    This allows you to easily get the mass equivalence between two species
    based on their molar mass and an assumption about the chemical reaction
    used to go between them.

    Examples
    --------
    >>> # assume that C <-> CO2 via C + O2 <-> CO2
    >>> get_mass_equivalence(12, 12 + 2 * 16, 1, 1)
    44 / 12

    >>> # assume that 3H2 + 2N -> 2NH3
    >>> get_mass_equivalence(2, 14, 3, 2)
    14 / 2 * 2 / 3 = 14 / 3

    >>> # the inclusion of stoichiometric ratios is why
    >>> # it doesn't really matter if it's H or H2
    >>> # assume that 3H + N -> NH3
    >>> get_mass_equivalence(1, 14, 3, 1)
    14 / 3
    """
    return (
        molar_mass_b
        / molar_mass_a
        * stoichiometric_coefficient_b
        / stoichiometric_coefficient_a
    )


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

        try:
            if unit in ["% of H2", "% H2 component of fuel"]:
            # assume the unit basically means % of H2 that leaks
            # per % of H2 used so the scale is simply 1 / 100 i.e.
            # go from % to kg H2 / kg H2 (i.e. kg H2 leaked/lost per 
            # kg H2 used)
                assert product == "H2"  # noqa: S101
                scale = 1 / 100
            elif unit in ["%", "% of fuel (LNG) consumption", "% NH3 used"]:
                assert product != "H2"  # noqa: S101
                scale = 1 / 100  # % => 0.01 * kg H2 / kg H2

                # kg H2 / kg H2
                #   => (kg H2 / kg H2) * (mass_factor_carrier * kg X / kg H2)
                #   => mass_factor_carrier * kg X / kg H2
                mass_factor = h2_mass_factor(carrier)

                # Should be larger (products are all heavier than H)
                assert mass_factor > 1  # noqa: S101
                scale = scale * mass_factor
            elif unit == "kgNH3/tNH3" or unit == "kgNOx/tNH3":
                # Derive the mass of NH3/NOx emissions per mass of H2
                # Only requires the NH3 mass factor to convert the denominator into H2
                # kg x/t NH3 => 0.001 * t NH3 / kg NH3 * kg x/t NH => 0.001 kg X / kg NH3
                #   => 0.001 kg X / kg NH3 * mass_factor_NH3 * kg NH3 / kg H2
                #   => 0.001 * mass_factor_NH3 kg X / kg H2
                scale = _get_unit_scaling("kg / t", "kg/kg") * h2_mass_factor("NH3")

                assert carrier == "NH3"  # noqa: S101
            else:
                raise ValueError(unit)  # noqa: TRY301
        except (SanitizeError, ValueError) as e:
            raise SanitizeError(unit, target_unit) from e

        result = ts * scale
        result["unit"] = target_unit
        return result

    return intensities.apply(_convert_intensities)
