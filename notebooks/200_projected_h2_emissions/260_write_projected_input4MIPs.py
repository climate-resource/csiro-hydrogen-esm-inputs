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
# In the previous step we gridded our updated timeseries. CSIRO needs a complete set of
# emissions, not just the sectors we updated.
#
# This step writes a set of emissions scenario outputs which conform with the existing
# input4MIPs data. We take output from the existing set of input4MIPs where we didn't
# make any changes.


# %%
import datetime
import logging

import xarray as xr
from joblib import Parallel, delayed  # type: ignore

from local.config import load_config_from_file
from local.h2_adjust.constants import HYDROGEN_PRODUCTS
from local.h2_adjust.outputs import (
    SupportsWriteSlice,
    find_gridded_slice,
    write_anthropogenic_AIR_slice,
    write_anthropogenic_slice,
)
from local.pydoit_nb.checklist import generate_directory_checklist

xr.set_options(keep_attrs=True)  # type: ignore
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
__version__ = config.input4mips_archive.version

# %%

gridded_data_directory = config.projected_gridding.output_directory
source_id = f"CR-{config.name.replace('_', '-')}"


def load_existing_data(variable_id: str, scenario_id: str) -> xr.Dataset | None:
    """
    Find an existing dataset from input4MIPs for a given variable and scenario

    These data are used to infill any sectors that were not modified.
    """
    exp_dir = config.input4mips_archive.local_archive / "CMIP6" / "ScenarioMIP" / "IAMC"

    scenario_glob = f"IAMC-*-{scenario_id.lower()}-1-1"
    variable_glob = f'{variable_id.replace("_", "-")}_*.nc'
    found_dirs = list(exp_dir.glob(scenario_glob))
    if len(found_dirs) == 1 and not found_dirs[0].exists():
        raise ValueError(  # noqa
            f"Could not find: {exp_dir}. Download the data from input4MIPs"
        )

    matches = list(exp_dir.rglob(f"{scenario_glob}/**/{variable_glob}"))

    if len(matches) > 1:
        raise ValueError(f"More than one match exists: {matches}")  # noqa
    if matches:
        return xr.load_dataset(matches[0])
    else:
        return None


# %%
common_meta = dict(
    contact="Jared Lewis (jared.lewis@climate-resource.com)",
    dataset_category="emissions",
    frequency="mon",
    further_info_url="https://gitlab.com/climate-resource/csiro/csiro-hydrogen-esm-inputs",
    institution="Climate Resource",
    institution_id="CR",
    nominal_resolution="50 km",
    realm="atmos",
    source="IAMC Scenario Database hosted at IIASA, with updated H2 assumptions",
    source_id=source_id,
    source_version=__version__,
    target_mip="ScenarioMIP",
    grid_label="gn",
)

# %%
# Use agriculture as a placeholder
# Other sectors are also read when generating the output files
non_aircraft_files = gridded_data_directory.glob("*Agriculture*.nc")
aircraft_files = gridded_data_directory.glob("*Aircraft*.nc")


# %%
def process_slice(
    func: SupportsWriteSlice,
    output_variable: str,
    year_slice: str,
    title: str,
    is_aircraft: bool,
):
    """
    Generate a input4MIPs data slice
    """
    # Assumes one slice per variable (i.e. all times in a single file)
    example_file = find_gridded_slice(
        output_variable,
        "Energy Sector" if not is_aircraft else "Aircraft",
        slice_years=year_slice,
        gridded_data_directory=gridded_data_directory,
    )
    if example_file is None:
        # N2O hasn't been gridded
        logger.error(f"Could not find example file for {output_variable}|{year_slice}")
        return
    baseline = load_existing_data(
        variable_id=output_variable, scenario_id=config.ssp_scenario
    )

    func(
        example_file,
        output_variable,
        version=config.input4mips_archive.version,
        years_slice=year_slice,
        common_meta={**common_meta, "title": title},
        root_data_directory=config.input4mips_archive.results_archive,
        gridded_data_directory=gridded_data_directory,
        baseline=baseline,
    )


# %%
jobs = []
for slice_path in non_aircraft_files:
    # Emissions_H2_Agriculture_Patterson_historical_190001-192512.nc
    year_slice = slice_path.stem.split("_")[-1]
    for out_var in HYDROGEN_PRODUCTS:
        jobs.append(
            (
                process_slice,
                write_anthropogenic_slice,
                out_var,
                year_slice,
                f"Future anthropogenic emissions of {out_var} prepared for CSIRO",
                False,
            )
        )

for slice_path in non_aircraft_files:
    year_slice = slice_path.stem.split("_")[-1]

    # Not all species grid aircraft emissions
    for out_var in ["NOx", "NH3", "H2"]:
        jobs.append(
            (
                process_slice,
                write_anthropogenic_AIR_slice,
                out_var,
                year_slice,
                f"Future anthropogenic aircraft emissions of {out_var} prepared for CSIRO",
                True,
            )
        )

len(jobs)

# %%
n_jobs = 4
Parallel(n_jobs=n_jobs)(delayed(f)(*args) for f, *args in jobs)

# %%
# Probably remove?
generate_directory_checklist(
    config.input4mips_archive.results_archive
    / "input4MIPs"
    / "CMIP6"
    / "ScenarioMIP"
    / "CR"
    / source_id
)

# %%
with open(config.input4mips_archive.complete_file_emissions_scenario, "w") as fh:
    fh.write(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
