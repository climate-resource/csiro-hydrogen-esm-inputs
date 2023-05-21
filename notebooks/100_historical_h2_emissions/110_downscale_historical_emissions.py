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
# # Country level downscaling of historical H2 data
#
# Take the sectoral delta emissions and downscale the R5 regional information to countries
#
# Aviation and International shipping are handled different from the other sectors. This is because CEDS only
# reports global totals for these sectors. These global totals are then used with a constant 2d pattern for
# shipping and a 3d pattern for aviation.

# %%
import os
import warnings

import bookshelf  # type: ignore
import domestic_pathways  # type: ignore # TODO: remove this dependency
import matplotlib.pyplot as plt  # type: ignore
import scmdata

from local.config import load_config_from_file
from local.h2_adjust.constants import WORLD_SECTORS
from local.h2_adjust.downscale import custom_region_mapping
from local.h2_adjust.timeseries import to_pyam
from local.h2_adjust.units import UNIT_REGISTRY

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%

config = load_config_from_file(config_file)

# %%
# Override the unit registry with scmdata's unit registry with added H2 support
domestic_pathways.utils.registry = UNIT_REGISTRY

# %%
shelf = bookshelf.BookShelf()
ceds = shelf.load("ceds", version="v2016_07_26").timeseries("by_sector_final")


# %%
HISTORICAL_END_YEAR = 2015

# %%
input_scenario_raw = (
    scmdata.ScmRun(str(config.historical_h2_emissions.baseline_h2_emissions_regions))
    .filter(type="anthropogenic", year=range(1850, HISTORICAL_END_YEAR + 1))
    .drop_meta(["sector_short", "type"])
)
input_scenario_raw["variable"] = (
    input_scenario_raw["variable"] + "|" + input_scenario_raw["sector"]
)
input_scenario_raw.timeseries()

# %%
scenario_to_downscale = input_scenario_raw.filter(sector=WORLD_SECTORS, keep=False)
scenario_to_downscale.get_unique_meta("variable")

# %%
# Historic/projected data are the same
# CEDS 2016 ends in 2014 so we extrapolate to 2015 using constant extrapolation
historic = (
    ceds.filter(variable="Emissions|CO", sector="Energy Sector")
    .drop_meta(["sector", "sector_short"])
    .interpolate(scenario_to_downscale["time"], extrapolation_type="constant")
)

projection = historic

downscaler = domestic_pathways.Downscaler(
    base_historic=to_pyam(historic),
    base_projection=to_pyam(projection),
    region_mapping=custom_region_mapping(),
)

# %% [markdown]
# ### Historical Emissions
#
# Use NOx as a template and overwrite with zeros

# %%
scenario_to_downscale.get_unique_meta("sector")

# %%
# Setting emissions in 1850 to zero
historic_emissions = ceds.drop_meta("sector_short").filter(
    year=1850, variable="Emissions|NOx"
)
historic_emissions["variable"] = (
    historic_emissions["variable"] + "|" + historic_emissions["sector"]
)

h2_emissions = historic_emissions
h2_emissions["variable"] = "Emissions|H2" + "|" + h2_emissions["sector"]
h2_emissions["model"] = "Blank"
h2_emissions["unit"] = "Mt H/yr"
h2_emissions = h2_emissions * 0
h2_emissions.timeseries()

# %%
# Check that the inputs have the same set of columns
assert all(scenario_to_downscale.meta.columns == h2_emissions.meta.columns)

# %%
variables_to_downscale = scenario_to_downscale.get_unique_meta("variable")
variables_to_downscale

# %%
for v in variables_to_downscale:
    hist = h2_emissions.filter(variable=v, log_if_empty=False)
    proj = scenario_to_downscale.filter(variable=v, log_if_empty=False)

    sector = hist.get_unique_meta("sector", True)
    v_short = v.split("|")[1]

    if not hist:
        print(f"No historical emissions for {v}")
        continue
    if not proj:
        print(f"No projections for Emissions|{v}")
        continue

    downscaler.add(
        domestic_pathways.Emission(
            sector,
            v_short,
            "aneris_hist_zero",
            historic_raw=to_pyam(hist.drop_meta("sector")),
            projection_raw=to_pyam(proj.drop_meta("sector")),
        )
    )

# %%
regions_of_interest = ["CHN", "EU27", "IND"]
sub_regions = historic_emissions.get_unique_meta("region")

# %%
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    downscaled_regions = scmdata.ScmRun(
        downscaler.downscale_to_sub_regions(
            sub_regions,
            downscaling_args={"intensity_reference": "Emissions|CO"},
        )
    )

# %%
# Add back sectoral information
downscaled_regions["sector"] = downscaled_regions["variable"].str.split("|").str[-1]

# %% [markdown]
# # Checks and write outputs

# %%
# Check harmonisation

for v in variables_to_downscale:
    plt.figure()
    plt.title(v)
    orig = scenario_to_downscale.filter(variable=v).filter(region="World", keep=False)
    orig["harmonisation"] = "raw"

    data = scmdata.run_append(
        [orig, downscaled_regions.filter(region="R5*", variable=v)]
    )
    data.lineplot(hue="harmonisation", style="region")

# %%
# Check totals
downscaled_regions_sum = downscaled_regions.process_over("region", "sum")
downscaled_regions_sum["region"] = "World"
downscaled_regions_sum = scmdata.ScmRun(downscaled_regions_sum)
temp = downscaled_regions_sum.filter(variable="*H2*", year=[1850, 2015]).timeseries()
temp.unstack("downscaling").round(3)

# %%
results_to_output = scmdata.run_append(
    [downscaled_regions, input_scenario_raw.filter(sector=WORLD_SECTORS)]
)

# %%
output_fname = os.path.join(
    config.historical_h2_emissions.baseline_h2_emissions_countries
)
results_to_output.timeseries(drop_all_nan_times=True).to_csv(output_fname)
