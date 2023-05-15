"""
Constants from the h2-adjust process
"""
from typing import Any

from attrs import define


@define
class InputRequirement:
    """
    Filters to apply to an input file
    """

    filters: dict[str, Any]
    checks: list[tuple[str, list[Any]]]


R5_REGIONS = ["R5.2ASIA", "R5.2LAM", "R5.2MAF", "R5.2OECD", "R5.2REF"]
START_YEAR = 2015
END_YEAR = 2100  # inclusive

HYDROGEN_CARRIERS = [
    "H2",
    "NH3",
    "CH4",
    "Synthetic Fuels",
]

# Sectors outside of this are ignored and any missing values are assumed to be zero
# Sectors match final gridding sectors from CEDS
# https://github.com/JGCRI/CEDS/blob/April-21-2021-release/input/gridding/gridding_mappings/CEDS_sector_to_gridding_sector_mapping.csv
HYDROGEN_SECTORS = [
    "International Shipping",
    "Energy Sector",
    "Aircraft",
    "Transportation Sector",
]

WORLD_SECTORS = [
    "Aircraft",  # CEDS aggregates aviation emissions to a global total
    "International Shipping",  # CEDS uses global total for gridding
]

HYDROGEN_PRODUCTS = ["H2", "NOx", "CH4", "NH3", "N2O"]
DOWNSCALING_VARIABLES = [
    # H2
    "Emissions|H2|Energy Sector",
    "Emissions|H2|Transportation Sector",
    "Emissions|H2|Aircraft",
    "Emissions|H2|International Shipping",
    # NOx
    "Emissions|NOx|Energy Sector",
    "Emissions|NOx|Transportation Sector",
    "Emissions|NOx|Aircraft",
    "Emissions|NOx|International Shipping",
    # CH4
    "Emissions|CH4|Energy Sector",
    "Emissions|CH4|Transportation Sector",
    # "Emissions|CH4|Aircraft",
    "Emissions|CH4|International Shipping",
    # NH3
    "Emissions|NH3|Energy Sector",
    "Emissions|NH3|Transportation Sector",
    "Emissions|NH3|Aircraft",
    "Emissions|NH3|International Shipping",
    # N2O
    "Emissions|N2O",
]


PALETTES = {
    "scenarios": {
        "MESSAGE-GLOBIOM SSP2-45": "#fa8c00",
        "IMAGE SSP1-19": "#006e55",
        "REMIND-MAGPIE SSP2-26": "#18a1cd",
    },
    "carriers": {
        "H2": "#005943",
        "NH3": "#00997E",
        "CH4": "#52E5C7",
        "Synthetic Fuels": "#C8FFF5",
    },
    "regions": {
        "R5.2ASIA": "#0D41E1",
        "R5.2LAM": "#0C63E7",
        "R5.2MAF": "#0A85ED",
        "R5.2OECD": "#09A6F3",
        "R5.2REF": "#07C8F9",
    },
}
