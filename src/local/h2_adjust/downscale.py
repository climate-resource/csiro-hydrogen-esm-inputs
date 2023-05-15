"""
Routines for downscaling R5 regions to country timeseries
"""

import domestic_pathways
import scmdata
from bookshelf import BookShelf

from local.h2_adjust.timeseries import to_pyam

shelf = BookShelf()


def get_historic_elements(ssp_scenario: str, end_year: int) -> scmdata.ScmRun:
    """
    Get the historical data used for downscaling

    In this specific case the ssp basic elements data are used.

    Parameters
    ----------
    ssp_scenario
        SSP scenario to use for downscaling
    end_year
        Year to clip data to

    Returns
    -------
        Clean historical data
    """
    ssp_elements = shelf.load("ssp-basic-elements", version="v2").timeseries(
        "by_country"
    )

    gdp_historical = ssp_elements.filter(
        variable="GDP|PPP",
        model="OECD Env-Growth",
        scenario=ssp_scenario,
    )

    # %%
    pop_historical = ssp_elements.filter(
        variable="Population",
        model="OECD Env-Growth",
        scenario=ssp_scenario,
    )

    assert len(gdp_historical) == len(pop_historical)  # noqa: S101
    return scmdata.run_append([gdp_historical, pop_historical]).filter(
        year=range(1850, end_year + 1)
    )


def get_projected_elements(ssp_scenario: str, start_year: int) -> scmdata.ScmRun:
    """
    Projected timeseries of interest

    Parameters
    ----------
    ssp_scenario
    start_year

    Returns
    -------
        Clean and filtered GDP and population data
    """
    ssp_elements = shelf.load("ssp-basic-elements", version="v2").timeseries(
        "by_country"
    )

    # %%
    pop_projection = ssp_elements.filter(
        variable="GDP|PPP",
        model="OECD Env-Growth",
        scenario=ssp_scenario,
        year=range(start_year, 2101),
    )

    # %%
    gdp_projection = ssp_elements.filter(
        variable="Population",
        model="OECD Env-Growth",
        scenario=ssp_scenario,
        year=range(start_year, 2101),
    )

    return scmdata.run_append([pop_projection, gdp_projection])


def prepare_downscaler(
    ssp_scenario: str, cutover_year: int
) -> domestic_pathways.Downscaler:
    """
    Prepare a downscaler for country downscaling

    # TODO: describe more

    Parameters
    ----------
    ssp_scenario
        SSP Scenario used for the projected information
    cutover_year
        Year to switch from historical information to projection information

    Returns
    -------
        Downscaler option initialised with the required timeseries
    """
    historic = get_historic_elements(ssp_scenario, cutover_year)
    projection = get_projected_elements(ssp_scenario, cutover_year)

    region_mapping = custom_region_mapping()
    # %%
    downscaler = domestic_pathways.Downscaler(
        base_historic=to_pyam(historic),
        base_projection=to_pyam(projection),
        region_mapping=region_mapping,
    )

    return downscaler


def custom_region_mapping() -> domestic_pathways.RegionMapping:
    """
    Region mapping for R5.2 regions

    Returns
    -------
        RegionMapping object for mapping the region names used
    """
    region_mapping = domestic_pathways.RegionMapping.from_model("R5_region")
    region_mapping.rename("R5ASIA", "R5.2ASIA")
    region_mapping.rename("R5MAF", "R5.2MAF")
    region_mapping.rename("R5OECD", "R5.2OECD")
    region_mapping.rename("R5LAM", "R5.2LAM")
    region_mapping.rename("R5REF", "R5.2REF")

    return region_mapping
