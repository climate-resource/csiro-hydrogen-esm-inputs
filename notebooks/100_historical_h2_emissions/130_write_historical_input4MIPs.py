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
# # Convert to input4MIPs format
#
# Converts the historical H2 emissions to an input4MIPs style file.
# Each file contains a single variable (always H2 in this case) with a number of
# sectors.
#
# The dataset is split into several timeslices for memory reasons
# Each timeslice is processed separetely. The slices are defined,
# by the previous gridding step


# %%
import logging

import xarray as xr
from joblib import Parallel, delayed  # type: ignore

from local import __version__
from local.config import load_config_from_file
from local.h2_adjust.outputs import (
    SupportsWriteSlice,
    find_gridded_slice,
    write_anthropogenic_AIR_slice,
    write_anthropogenic_slice,
)
from local.pydoit_nb.checklist import generate_directory_checklist

xr.set_options(keep_attrs=True)  # type: ignore
logging.basicConfig(level=logging.INFO)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)


# %%
gridded_data_directory = config.historical_h2_gridding.output_directory

common_meta = dict(
    contact="Jared Lewis (jared.lewis@climate-resource.com)",
    dataset_category="emissions",
    frequency="mon",
    further_info_url="https://gitlab.com/climate-resource/csiro/csiro-hydrogen-esm-inputs",
    institution="Climate Resource",
    institution_id="CR",
    nominal_resolution="50 km",
    realm="atmos",
    source="h2-adjust",
    source_id="CR-historical",
    source_version=__version__,
    target_mip="CMIP",
    grid_label="gn",
)


# %%
jobs = []


# Use agriculture as a placeholder
# Other sectors are also read when generating the output files
non_aircraft_files = gridded_data_directory.glob("*Agriculture*.nc")
aircraft_files = gridded_data_directory.glob("*Aircraft*.nc")


def process_slice(func: SupportsWriteSlice, year_slice: str, title: str) -> None:
    """
    Generate a historical input4MIPs data slice
    """
    # Checks that there is a single matching slice
    example_file = find_gridded_slice(
        "H2",
        "Energy Sector",
        slice_years=year_slice,
        gridded_data_directory=gridded_data_directory,
    )

    if example_file is None:
        return
    func(
        example_file,
        "H2",
        version=config.input4mips_archive.version,
        years_slice=year_slice,
        common_meta={**common_meta, "title": title},
        root_data_directory=config.input4mips_archive.results_archive,
        gridded_data_directory=gridded_data_directory,
        baseline=None,
    )


# %%
for slice_path in non_aircraft_files:
    # Emissions_H2_Agriculture_Patterson_historical_190001-192512.nc
    year_slice = slice_path.stem.split("_")[-1]

    jobs.append(
        (
            process_slice,
            write_anthropogenic_slice,
            year_slice,
            "Historical anthropogenic emissions of H2 prepared for CSIRO",
        )
    )

for slice_path in aircraft_files:
    year_slice = slice_path.stem.split("_")[-1]
    jobs.append(
        (
            process_slice,
            write_anthropogenic_AIR_slice,
            year_slice,
            "Historical anthropogenic aircraft emissions of H2 prepared for CSIRO",
        )
    )

len(jobs)


# %%
n_jobs = 2
Parallel(n_jobs=n_jobs)(delayed(f)(*args) for f, *args in jobs)

# %%

generate_directory_checklist(
    config.input4mips_archive.results_archive
    / "input4MIPs"
    / "CMIP6"
    / "CMIP"
    / "CR"
    / "CR-historical"
)
