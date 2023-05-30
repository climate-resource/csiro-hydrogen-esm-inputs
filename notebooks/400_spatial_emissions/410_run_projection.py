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
# # Run Projection
#
# From a set of config, generate the projected data set for all of the desired timeslices

# %%
# Load environment variables
# Used to determine where input4MIPs data is stored
import dotenv

dotenv.load_dotenv()

# %%
import logging
import os

import xarray as xr
from spaemis.config import load_config
from spaemis.input_data import database, load_timeseries
from spaemis.inventory import clip_region, load_inventory, write_inventory_csvs
from spaemis.project import calculate_point_sources, calculate_projections

from local.config import ConfigSpatialEmissions, load_config_from_file

logger = logging.getLogger("200_run_projection")
logging.basicConfig(level=logging.INFO)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file
name: str = "ssp119_australia"

# %%
config = load_config_from_file(config_file)


def find_config_match(iterable: list[ConfigSpatialEmissions]) -> ConfigSpatialEmissions:
    """Get the first spatial emissions config with a matching name"""
    return next(run_config for run_config in iterable if run_config.name == name)


spaemis_config = find_config_match(config.spatial_emissions)

# %%
downscaling_config = load_config(str(spaemis_config.downscaling_config))
downscaling_config

# %%
# Setup input4MIPs directory
database.register_path(str(config.input4mips_archive.results_archive))
database.register_path(str(config.input4mips_archive.local_archive))
assert len(database.paths)
database.paths

# Set up the proxy data directory
os.environ.setdefault("SPAEMIS_PROXY_DIRECTORY", str(spaemis_config.proxy_directory))
os.environ.setdefault(
    "SPAEMIS_INVENTORY_DIRECTORY", str(spaemis_config.inventory_directory)
)
os.environ.setdefault(
    "SPAEMIS_POINT_SOURCE_DIRECTORY", str(spaemis_config.point_source_directory)
)
# %%
inventory = load_inventory(
    downscaling_config.inventory.name,
    downscaling_config.inventory.year,
)
inventory

if downscaling_config.input_timeseries:
    timeseries = load_timeseries(downscaling_config.input_timeseries)
else:
    timeseries = {}

# %%
dataset = calculate_projections(downscaling_config, inventory, timeseries=timeseries)
dataset


# %%
def _show_variable_sums(da):
    if "year" not in da.coords:
        da = da.copy()
        da["year"] = "unknown"
        da = da.expand_dims(["year"])

    # Results are all in kg/cell/yr so can be summed like this
    totals = da.sum(dim=("sector", "lat", "lon")).to_dataframe() / 1000 / 1000

    return totals.round(3)  # kt / yr


_show_variable_sums(dataset)

# %%
point_sources = calculate_point_sources(downscaling_config, inventory)
point_sources

# %%

if len(point_sources):
    _show_variable_sums(point_sources)

# %%
if len(point_sources):
    point_sources["H2"].sel(sector="industry").plot()

# %%
# Align and merge point sources
# dataset has nans outside of the clipped region. PointSources in those areas are ignored.
merged, temp = xr.align(dataset.fillna(0), point_sources, join="outer", fill_value=0)

for variable in temp.data_vars:
    if variable not in merged.data_vars:
        merged[variable] = temp[variable]
    else:
        merged[variable] += temp[variable]

del temp  # Save memory
merged = clip_region(merged, inventory.border_mask)

# %%
_show_variable_sums(merged)

# %%
dataset["H2"].sum(dim="sector").plot(robust=True, col="year")

# %%
for variable in merged.data_vars:
    merged[variable].plot(robust=True, col="year", row="sector")

# %%
logger.info("Writing output dataset as netcdf")
spaemis_config.netcdf_output.parent.mkdir(parents=True, exist_ok=True)
merged.to_netcdf(spaemis_config.netcdf_output)

# %%
logger.info("Writing CSV files")
for year in downscaling_config.timeslices:
    target_dir = spaemis_config.csv_output_directory / str(year)
    data_to_write = merged.sel(year=year)

    target_dir.mkdir(exist_ok=True, parents=True)
    write_inventory_csvs(data_to_write, str(target_dir))
