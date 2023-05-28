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
# # Extract grids from CMIP6
#
# Extract the gridding patterns from the CMIP6 data. Using these ensures that we have a smooth transition between the CMIP6 historical data and our updated projections.

# %%
from pathlib import Path

import cf_xarray.units
import matplotlib.pyplot as plt  # type: ignore
import numpy as np
import pint_xarray  # type: ignore
import tqdm.autonotebook as tqdman
import xarray as xr
from carpet_concentrations.gridders import LatitudeSeasonalityGridder
from carpet_concentrations.time import (
    convert_time_to_year_month,
    convert_year_month_to_time,
)
from carpet_concentrations.xarray_utils import (
    calculate_weighted_area_mean_latitude_only,
)

from local.config import load_config_from_file

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
cf_xarray.units.units.define("ppm = 1 / 1000000")
cf_xarray.units.units.define("ppb = ppm / 1000")

# %%
pint_xarray.accessors.default_registry = pint_xarray.setup_registry(
    cf_xarray.units.units
)

# %%
UNIT_MAP = {
    "1.e-6": "ppm",
    "1.e-9": "ppb",
}

# %%
OUTPUT_FILE = (
    config.concentration_gridding.cmip6_seasonality_and_latitudinal_gradient_path
)
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE


# %% [markdown]
# ## Extract grids


# %%
def get_seasonality_and_lat_gradient(gridded, global_mean):
    """
    Get seasonality and latitudinal gradient
    """
    return gridded - global_mean


# %%
def get_gridding_values(seasonality_and_latitudinal_gradient, variable):
    """
    Get gridding values
    """
    latitudinal_gradient = seasonality_and_latitudinal_gradient.groupby(
        "time.year"
    ).mean("time")
    latitudinal_gradient_monthly = convert_year_month_to_time(
        latitudinal_gradient
        * xr.DataArray(np.ones(12), dims=("month",), coords={"month": range(1, 13)})
    )

    seasonality = (
        convert_year_month_to_time(
            convert_time_to_year_month(seasonality_and_latitudinal_gradient)
        )
        - latitudinal_gradient_monthly
    )

    # check seasonality annual-mean is close to zero
    np.testing.assert_allclose(
        seasonality.groupby("time.year").mean("time")[variable].data, 0, atol=1e-5
    )
    seasonality_gridding = convert_time_to_year_month(
        seasonality[variable].drop("sector")
    )
    seasonality_gridding["lat"].attrs["units"] = "degrees"
    seasonality_gridding = seasonality_gridding.pint.quantify()

    latitudinal_gradient_gridding = convert_time_to_year_month(
        latitudinal_gradient_monthly[variable].drop("sector")
    )
    latitudinal_gradient_gridding["lat"].attrs["units"] = "degrees"
    latitudinal_gradient_gridding = latitudinal_gradient_gridding.pint.quantify()

    # force area mean to zero after checking it is close to zero
    area_mean = calculate_weighted_area_mean_latitude_only(
        latitudinal_gradient_gridding.to_dataset()
        .cf.add_bounds("lat")
        .pint.quantify(lat_bounds="degrees", lat="degrees"),
        variables=[variable],
    )[variable]
    np.testing.assert_allclose(area_mean.data.magnitude, 0, atol=1e-4)

    latitudinal_gradient_gridding = latitudinal_gradient_gridding - area_mean

    gridding_values = xr.Dataset(
        {
            #             f"seasonality_{variable}": seasonality_gridding,
            #             f"latitudinal-gradient_{variable}": latitudinal_gradient_gridding,
            "seasonality": seasonality_gridding,
            "latitudinal_gradient": latitudinal_gradient_gridding,
        }
    )
    gridding_values = gridding_values.cf.add_bounds("lat").pint.quantify(
        lat_bounds="degrees", lat="degrees"
    )

    return gridding_values


# %%
available_files: dict[str, dict[tuple[str, str], Path]] = {"gridded": {}, "gmnhsh": {}}
for f in config.cmip6_concentrations.root_raw_data_dir.glob("*.nc"):
    toks = f.name.split("_")
    variable = toks[0]
    scenario_full = toks[-3]
    scenario = [
        s
        for s in config.cmip6_concentrations.concentration_scenario_ids
        if s in scenario_full
    ][0]
    grid = toks[-2]

    if grid == "gr1-GMNHSH":
        available_files["gmnhsh"][(scenario, variable)] = f
    elif grid == "gn-15x360deg":
        available_files["gridded"][(scenario, variable)] = f
    else:
        raise NotImplementedError(grid)

# %%
all_gridding_values = []
for scenario in tqdman.tqdm(
    config.cmip6_concentrations.concentration_scenario_ids, desc="scenario"
):
    for variable in tqdman.tqdm(
        config.cmip6_concentrations.concentration_variables,
        desc="variable",
        leave=False,
    ):
        variable_under = variable.replace("-", "_")

        # file paths
        gridded_file = available_files["gridded"][(scenario, variable)]
        global_mean_file = available_files["gmnhsh"][(scenario, variable)]

        # load data
        gridded_data = xr.load_dataset(gridded_file)
        gridded_data = gridded_data.pint.quantify(
            {variable_under: UNIT_MAP[gridded_data[variable_under].attrs["units"]]},
            unit_registry=cf_xarray.units.units,
        )
        global_mean_data = xr.load_dataset(global_mean_file)
        global_mean_data = global_mean_data.pint.quantify(
            {variable_under: UNIT_MAP[global_mean_data[variable_under].attrs["units"]]},
            unit_registry=cf_xarray.units.units,
        )

        seasonality_and_lat_gradient = get_seasonality_and_lat_gradient(
            gridded=gridded_data, global_mean=global_mean_data.sel(sector=0)
        )

        gridding_values = get_gridding_values(
            seasonality_and_lat_gradient,
            variable_under,
        )

        # check that we can use these gridding values with our gridding class
        LatitudeSeasonalityGridder(gridding_values)
        to_keep = gridding_values.expand_dims(
            scenario=[scenario], variable=[variable_under]
        )
        all_gridding_values.append(to_keep.pint.to("ppm"))

# %%
all_gridding_values = xr.merge(all_gridding_values)  # type: ignore
all_gridding_values

# %%
tmp = all_gridding_values.pint.dequantify()  # type: ignore
tmp.to_netcdf(OUTPUT_FILE)
OUTPUT_FILE

# %%
convert_year_month_to_time(
    all_gridding_values["latitudinal_gradient"],  # type: ignore
).sel(
    variable=[variable_under]
).plot.pcolormesh(  # type: ignore
    x="time", y="lat", cmap="rocket_r", levels=100, row="scenario", col="variable"
)
plt.show()

# %%
gridded_data[variable_under].plot.pcolormesh(
    x="time", y="lat", cmap="rocket_r", levels=100
)
plt.show()

# %%
seasonality_and_lat_gradient[variable_under].plot.pcolormesh(
    x="time", y="lat", cmap="rocket_r", levels=100
)
plt.show()

# %%
seasonality_and_lat_gradient.sel(lat=[-87.5, 0, 87.5], method="nearest").sel(
    time=seasonality_and_lat_gradient["time.year"].isin(range(2015, 2016 + 1))
)[variable_under].plot.line(hue="lat")
plt.grid()
plt.show()

# %%
latitudinal_gradient = seasonality_and_lat_gradient.groupby("time.year").mean("time")
latitudinal_gradient.sel(year=latitudinal_gradient["year"].isin(range(2015, 2100 + 1)))[
    variable_under
].plot.line(hue="lat")
plt.grid()
plt.show()

# %%
gridding_values_time = convert_year_month_to_time(gridding_values)

# %%
gridding_values_time["latitudinal_gradient"].sel(
    time=gridding_values_time["time.year"].isin(range(2051, 2053 + 1))
).plot.line(hue="lat")
plt.grid()
plt.show()

# %%
gridding_values_time["seasonality"].sel(
    time=gridding_values_time["time.year"].isin(range(2015, 2017 + 1))
).plot.line(hue="lat")

plt.grid()
plt.show()
