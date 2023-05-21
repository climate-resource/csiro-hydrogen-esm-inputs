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
# # Country level downscaling
#
# Take the sectoral delta emissions and downscale the R5 regional information to countries
#
# Aviation and International shipping are handled different from the other sectors.
# This is because CEDS only
# reports global totals for these sectors. These global totals are then used with a constant 2d pattern for
# shipping and a 3d pattern for aviation.

# %%
import re
import warnings
from datetime import datetime

import bookshelf  # type: ignore
import domestic_pathways  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import scmdata.units

from local.config import load_config_from_file
from local.h2_adjust.constants import WORLD_SECTORS
from local.h2_adjust.downscale import prepare_downscaler
from local.h2_adjust.timeseries import to_pyam
from local.h2_adjust.units import UNIT_REGISTRY

# %%
# Override the unit registry with scmdata's unit registry with added H2 support
domestic_pathways.utils.registry = UNIT_REGISTRY

# %% tags=["parameters"]
config_file: str = "output-bundles/20230516/ssp119/ssp119.yaml"  # config file

# %%
config = load_config_from_file(config_file)


# %% [markdown]
# We are cheating a bit here and using the basic elements for both the historical and projections. It is a
# bit of a simpler set up compared to using WDI.
#
# ```
# historical emissions: CEDS
# historical gdp: WDI
# historical population: WDI
#
# projection gdp: ssp database
# projection population: ssp database
# ```

# %%
shelf = bookshelf.BookShelf()
ceds = shelf.load("ceds", version="v2016_07_26").timeseries("by_sector_final")

# %%
HISTORICAL_END_YEAR = 2015
YEARS_OF_INTEREST = [2015, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]

# %%
input_scenario_raw = scmdata.ScmRun(config.emissions.complete_scenario).filter(
    source="adjusted"
)
input_scenario_raw.get_unique_meta("variable")

# %%
scenario_to_downscale = input_scenario_raw.filter(modified=True).filter(
    sector=WORLD_SECTORS, keep=False
)
assumptions = scenario_to_downscale.get_unique_meta("assumptions", True)
scenario_to_downscale = scenario_to_downscale.drop_meta(
    ["assumptions", "source", "modified"]
)

scenario_to_downscale.get_unique_meta("variable")

# %%
scenario_to_downscale

# %%
# Extract SSP from scenario
scenario_name = scenario_to_downscale.get_unique_meta("scenario", True)
match = re.match("SSP(\\d)", scenario_name, flags=re.IGNORECASE)
if match is None:
    raise ValueError("Could not determine SSP number")  # noqa
ssp_number = int(match.group(1))
ssp_scenario = f"SSP{ssp_number}"
ssp_scenario

# %%
downscaler = prepare_downscaler(ssp_scenario, HISTORICAL_END_YEAR)

# %% [markdown]
# ### Historical Emissions
#
# Sourced from CEDS

# %%
scenario_to_downscale.get_unique_meta("sector")

# %%
# CEDS data only goes to 2014 so there isn't any overlap
# TODO: check if we should do something different than extrapolation
historic_emissions = (
    ceds.drop_meta("sector_short")
    .filter(year=range(1900, HISTORICAL_END_YEAR + 1))
    .interpolate(
        [datetime(y, 1, 1) for y in range(1850, HISTORICAL_END_YEAR + 1)],
        extrapolation_type="constant",
    )
)
historic_emissions["variable"] = (
    historic_emissions["variable"] + "|" + historic_emissions["sector"]
)
historic_emissions.get_unique_meta("sector")

# %% [markdown]
# ### H2 emissions
#
# CEDs doesn't provide any historical values for H2. Instead we use our
# historical country downscaled emissions from 100_historical/300.
# These use Emissions|CO as a proxy for downscaling

# %%
h2_emissions = (
    scmdata.ScmRun(config.historical_h2_emissions.baseline_h2_emissions_countries)
    .filter(downscaling="hist_zero")
    .drop_meta(["downscaling", "harmonisation"])
)
h2_emissions

# %%
historic_emissions = historic_emissions.append(h2_emissions)

# %%
# Need to handle the unit conversion as aneris can't handle the custom context
for _, meta in (
    historic_emissions.meta[["variable", "unit"]].drop_duplicates().iterrows()
):
    scenario_to_downscale = scenario_to_downscale.convert_unit(
        meta.unit, variable=meta.variable, context="NOx_conversions"
    ).drop_meta("unit_context")

scenario_to_downscale.meta[["variable", "unit"]].drop_duplicates().merge(
    historic_emissions.meta[["variable", "unit"]].drop_duplicates(),
    left_on="variable",
    right_on="variable",
)

# %%
# Check that the inputs have the same set of columns
assert all(scenario_to_downscale.meta.columns == historic_emissions.meta.columns)

# %%
variables_to_downscale = scenario_to_downscale.get_unique_meta("variable")
variables_to_downscale


assert historic_emissions["year"].max() == HISTORICAL_END_YEAR
assert scenario_to_downscale["year"].min() == HISTORICAL_END_YEAR

# %%
for v in variables_to_downscale:
    hist = historic_emissions.filter(variable=v, log_if_empty=False)
    proj = scenario_to_downscale.filter(variable=v, log_if_empty=False)

    v_short = v.split("|")[1]

    if not hist:
        print(f"No historical emissions for {v}")
        continue
    if not proj:
        print(f"No projections for Emissions|{v}")
        continue
    sector = hist.get_unique_meta("sector", True)

    downscaler.add(
        domestic_pathways.Emission(
            sector,
            v_short,
            "intensity_convergence",
            historic_raw=to_pyam(hist.drop_meta("sector")),
            projection_raw=to_pyam(proj.drop_meta("sector")),
        )
    )

# %%
regions_of_interest = ["CHN", "EU27", "IND"]
sub_regions = historic_emissions.get_unique_meta("region")

# %%

# for variable in variables_to_downscale:

# %%
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    downscaled_regions = scmdata.ScmRun(
        downscaler.downscale_to_sub_regions(sub_regions, harmonisation_method="aneris")
    )

# %% [markdown]
# # Checks and write outputs

# %%
# Calculate region aggregates
historic_aggregates = scmdata.run_append(
    [
        historic_emissions.filter(
            region=downscaler.region_mapping.get_sub_regions(r), log_if_empty=False
        ).process_over("region", "sum", op_cols={"region": r}, as_run=True)
        for r in scenario_to_downscale.get_unique_meta("region")
    ]
)
historic_aggregates

# %%
# Check harmonisation

for v in variables_to_downscale:
    plt.figure()
    plt.title(v)
    orig = scenario_to_downscale.filter(variable=v).filter(region="World", keep=False)
    orig["harmonisation"] = "raw"
    historic_aggregates["harmonisation"] = "historical"

    data = scmdata.run_append(
        [
            orig,
            downscaled_regions.filter(region="R5*", variable=v),
            historic_aggregates.filter(variable=v),
        ]
    )
    data.lineplot(hue="harmonisation", style="region")

# %%
scenario_to_downscale.filter(region="R5*").process_over(
    "region", "sum", as_run=True, op_cols={"region": "World"}
).filter(variable="*NOx*", year=[2015, 2100]).timeseries()

# %%
# Check totals
downscaled_regions_sum = downscaled_regions.process_over("region", "sum")
downscaled_regions_sum["region"] = "World"
downscaled_regions_sum = scmdata.ScmRun(downscaled_regions_sum)
downscaled_regions_sum.filter(variable="*NOx*", year=[2015, 2100]).timeseries().unstack(
    "downscaling"
).round(3)

# %%
results_to_output = scmdata.run_append(
    [downscaled_regions, input_scenario_raw.filter(sector=WORLD_SECTORS)]
)
results_to_output["assumptions"] = assumptions

# %%

results_to_output.filter(year=YEARS_OF_INTEREST).timeseries(
    drop_all_nan_times=True
).to_csv(config.emissions.complete_scenario_countries)

# %%
