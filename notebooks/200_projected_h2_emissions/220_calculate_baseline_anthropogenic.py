# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Calculate baseline natural and anthropogenic H2 emissions
#
# These H2 emissions are not modified as part of the emissions intensities, but have been
# quantified by other studies (see
# `docs/Literature review on anthropogenic and natural global H2 sources and sinks_9Aug2022.docx`)
# We are only modelling sources


# %%
from __future__ import annotations

import logging

import bookshelf  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import numpy.testing as npt
import pandas as pd
import scmdata

import local.h2_adjust.units  # noqa Support H2 units
from local.config import load_config_from_file
from local.h2_adjust.constants import WORLD_SECTORS

# %%
logger = logging.getLogger()


# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%

config = load_config_from_file(config_file)

# %%
plt.rcParams["figure.figsize"] = (12, 8)
baseline_config = config.projected_h2_emissions

# %% [markdown]
# # Load data
#
# ## Bookshelf data

# %%
shelf = bookshelf.BookShelf()
scenario = "historical"

rcmip_book = shelf.load("rcmip-emissions")
ceds_book = shelf.load("ceds", version="v2016_07_26")

proxy_emissions = (
    rcmip_book.timeseries("complete")
    .filter(scenario=baseline_config.scenario, region="World", year=range(1850, 2101))
    .resample("AS")
).drop_meta(["activity_id", "mip_era"])
proxy_emissions.get_unique_meta("variable")

# %%
ceds_data = ceds_book.timeseries("by_sector_final")

# %%
# Filter out "International Shipping" as they are all zero (except for NMVOC,
# but the total was much less than the global total)
# TODO: fix in bookshelf
ceds_data_global = ceds_data.filter(
    sector="International Shipping", keep=False
).process_over("region", "sum", op_cols={"region": "World"}, as_run=True)

# Rename "International shipping" to "International Shipping"
ceds_data_shipping = ceds_data_global.filter(sector="International shipping")
ceds_data_shipping["sector"] = "International Shipping"
ceds_data_global = scmdata.run_append(
    [
        ceds_data_global.filter(sector="International shipping", keep=False),
        ceds_data_shipping,
    ]
)
ceds_data_global.get_unique_meta("variable")

# %% [markdown]
# ## Baseline assumptions

# %%
# Baseline values to scale
# These are formatted as a scmrun with a single year. The year is used to calculate
# the ratio used to scale
baseline_values = scmdata.ScmRun(str(baseline_config.baseline_source))
# We only support scaling from a single annual value
year_to_scale = int(baseline_values["year"].unique()[0])
year_to_scale

# %% [markdown]
# # Anthropogenic Emissions

# %%

# The proxy timeseries used to scale the anthropogenic baseline H2 emissions
# CEDs data used to split up sectors
anthropogenic_proxy = baseline_config.anthropogenic_proxy
print(anthropogenic_proxy)


# %%


def scale_by_proxy(baseline: pd.DataFrame | scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Scale a single value by a proxy timeseries to produce a timeseries
    """
    baseline_run = scmdata.ScmRun(baseline)
    proxy_variable = anthropogenic_proxy[baseline_run.get_unique_meta("variable", True)]

    proxy = proxy_emissions.filter(variable=proxy_variable, region="World")
    assert len(proxy) == 1

    ratio = (
        baseline_run.values.squeeze()
        / proxy.filter(year=year_to_scale).values.squeeze()
    )

    scaled_timeseries = proxy * ratio
    for c in set(baseline_run.meta.columns) - {"scenario"}:
        scaled_timeseries[c] = baseline_run[c]

    return scaled_timeseries


scaled_emissions = scmdata.ScmRun(
    baseline_values.filter(type="anthropogenic", variable=anthropogenic_proxy.keys())
    .groupby("variable")
    .apply(scale_by_proxy)
    .filter(year=range(1850, 2101))
)
scaled_emissions.timeseries()

# %%
# Check that the values in `year_to_scale` match
for v in baseline_values.filter(type="anthropogenic").get_unique_meta("variable"):
    npt.assert_allclose(
        baseline_values.filter(
            type="anthropogenic", variable=v, year=year_to_scale
        ).values.squeeze(),
        scaled_emissions.filter(variable=v, year=year_to_scale).values.squeeze(),
    )

# %%
# Plot to verify that the scaling worked as intended
scaled_emissions.lineplot(hue="variable")


# %%
scaled_emissions.process_over(
    "variable", "sum", op_cols={"variable": "Emissions|H2"}, as_run=True
).lineplot(hue="variable")


# %% [markdown]
# ## Break down to CEDs

# %% [markdown]
# These emissions now need to be split into CEDs sectors
#
# One option would be to use the CEDs sectoral breakdown for a given species (maybe with some filtering)?
#
# i.e.
#


# %%
def calc_sector_weights(values: scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Calculate weights for a given sector
    """
    assert len(values) == len(values.get_unique_meta("sector"))

    weights = values.timeseries() / values.values.sum(axis=0)
    npt.assert_allclose(weights.sum(axis=0), 1)

    weights = scmdata.ScmRun(weights)
    weights["variable"] = "Sector weights"
    weights["unit"] = "1"

    return weights


# %%
calc_sector_weights(ceds_data_global.filter(variable="Emissions|CO")).lineplot(
    hue="sector"
)

# %% [markdown]
# Methane scaling is a bit annoying as CEDs only goes back to 1970 for CH4. A
# quick check suggests that the sector weights are relatively flat so can be
# extended back in time.
#
# We are using constant extrapolation to fill in the gaps

# %%
methane_weights = calc_sector_weights(
    ceds_data_global.filter(variable="Emissions|CH4", year=range(1970, 2101))
)
methane_weights.lineplot(hue="sector")

# %%
methane_weights.interpolate(
    scaled_emissions["time"], extrapolation_type="constant"
).lineplot(hue="sector")

# %%
ceds_sectors = config.projected_h2_emissions.ceds_breakdown_sectors
ceds_sectors

# %%
sector_scales = {}

for v in anthropogenic_proxy:
    proxy_variable = anthropogenic_proxy[v]
    ceds_variable = "|".join(proxy_variable.split("|")[:2])
    ceds_sectors_v = ceds_sectors[v]
    historical_emissions = ceds_data_global.filter(
        sector=ceds_sectors_v, variable=ceds_variable
    )

    if historical_emissions.shape[0] == 1:
        tmp = historical_emissions.copy()
        tmp["unit"] = 1
        tmp["variable"] = "Sector weights"
        tmp.values[:, :] = 1
        sector_scales[v] = tmp.interpolate(
            scaled_emissions["time"], extrapolation_type="constant"
        )
        continue

    if "CH4" in proxy_variable:
        historical_emissions = historical_emissions.filter(year=range(1970, 2101))

    sector_scales[v] = calc_sector_weights(historical_emissions).interpolate(
        scaled_emissions["time"], extrapolation_type="constant"
    )


# %%
def apply_sector_split(emissions: scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Split a set of variable into a sectoral breakdown

    The split is calculated using the `anthropogenic_proxy` mapping
    """
    emissions = scmdata.ScmRun(emissions)
    scale = sector_scales[emissions.get_unique_meta("variable", True)]

    # Assumes that the sector scaler and the emissions have the same timebase
    npt.assert_allclose(scale["year"], emissions["year"])
    assert len(emissions) == 1
    sectoral_emissions = scmdata.ScmRun(scale.timeseries() * emissions.values)
    for c in emissions.meta.columns:
        sectoral_emissions[c] = emissions[c]
    sectoral_emissions["source"] = sectoral_emissions["variable"]
    sectoral_emissions["variable"] = "Emissions|H2"
    return sectoral_emissions


# Apply the sector scale factors to the scaled emissions
sectoral_emissions = scmdata.ScmRun(
    scaled_emissions.groupby("variable").apply(apply_sector_split)
).convert_unit("Mt H2/yr")
sectoral_emissions.timeseries()

# %%
total_sectoral_emissions = sectoral_emissions.process_over(
    ["source"], "sum", as_run=True
)

# %% [markdown]
# # Apply region dissagregation

# %%
rcmip_emms = rcmip_book.timeseries("magicc")
rcmip_emms["region"] = rcmip_emms["region"].str.replace("World|", "", regex=False)

# %%
rcmip_co = rcmip_emms.filter(
    scenario=scenario, variable="Emissions|CO", year=range(1850, 2101)
).resample("AS")
rcmip_co

# %%
rcmip_co_factor = scmdata.ScmRun(
    rcmip_co.filter(region="World", keep=False).timeseries()
    / rcmip_co.filter(region="World").values,
).filter(year=total_sectoral_emissions["year"].values)
rcmip_co_factor["variable"] = "Region Weighting"
rcmip_co_factor["unit"] = "dimensionless"
rcmip_co_factor.timeseries().sum(axis=0)


# %%
def apply_region_split(emissions: scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Split a global emissions timeseries into regions

    The regional breakdown of CO emissions is used as a proxy
    """
    if emissions.get_unique_meta("sector", True) in WORLD_SECTORS:
        return emissions

    regional_emissions = [emissions]

    for r in rcmip_co_factor.get_unique_meta("region"):
        region_emms = scmdata.ScmRun(
            emissions.timeseries() * rcmip_co_factor.filter(region=r).values
        )
        region_emms["region"] = r
        regional_emissions.append(region_emms)

    return scmdata.run_append(regional_emissions)


sectoral_regional_emissions = total_sectoral_emissions.groupby(
    ("variable", "sector")
).apply(apply_region_split)
sectoral_regional_emissions

# %% [markdown]
# ## Plots

# %%
plt.figure(figsize=(12, 8))

totals = sectoral_emissions.process_over(["source"], "sum", as_run=True)
totals = totals.append(
    totals.process_over(
        ["sector", "sector_short"], "sum", as_run=True, op_cols={"sector": "Total"}
    )
)

totals.lineplot(hue="sector")

# Create plot directories
# this assumes that all figures go in the same directory
baseline_config.figure_baseline_by_sector.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(baseline_config.figure_baseline_by_sector)

# %%
fig = plt.figure(figsize=(12, 8))

totals = sectoral_emissions.process_over(
    ["variable", "sector", "sector_short"],
    "sum",
    as_run=True,
    op_cols={"variable": "Emissions|H2"},
)
totals = totals.append(
    totals.process_over(["source"], "sum", as_run=True, op_cols={"source": "Total"})
)

totals.lineplot(hue="source")

plt.savefig(baseline_config.figure_baseline_by_source)

# %%
axs = plt.figure(figsize=(12, 8 * 4)).subplots(4)

for i, source in enumerate(sectoral_emissions.groupby("source")):
    ax = axs[i]
    ax.set_title(source.get_unique_meta("source", True))
    source.lineplot(ax=ax, hue="sector")

plt.tight_layout()
plt.savefig(baseline_config.figure_baseline_by_source_and_sector)

# %%
sectoral_regional_emissions["scenario"] = scenario
baseline_config.baseline_h2_emissions_regions.parent.mkdir(parents=True, exist_ok=True)
sectoral_regional_emissions.filter(year=range(2015, 2101)).to_csv(
    baseline_config.baseline_h2_emissions_regions
)

# %%
