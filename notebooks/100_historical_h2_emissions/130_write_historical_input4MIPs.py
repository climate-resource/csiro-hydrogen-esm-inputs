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
import logging
from collections.abc import Iterable

import xarray as xr
from joblib import Parallel, delayed  # type: ignore

from local import __version__
from local.config import load_config_from_file
from local.h2_adjust.outputs import (
    GriddedAircraftEmissionsDataset,
    GriddedEmissionsDataset,
    Input4MIPsMetadata,
)

xr.set_options(keep_attrs=True)  # type: ignore
logging.basicConfig(level=logging.INFO)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
SECTOR_MAP = [
    "Agriculture",
    "Energy Sector",
    "Industrial Sector",
    "Transportation Sector",
    "Residential, Commercial, Other",
    "Solvents production and application",
    "Waste",
    "International Shipping",
    # "Negative CO2 Emissions", # CO2 also includes this additional sector, but we aren't regridding that here
]
LEVELS = [
    0.305,
    0.915,
    1.525,
    2.135,
    2.745,
    3.355,
    3.965,
    4.575,
    5.185,
    5.795,
    6.405,
    7.015,
    7.625,
    8.235,
    8.845,
    9.455,
    10.065,
    10.675,
    11.285,
    11.895,
    12.505,
    13.115,
    13.725,
    14.335,
    14.945,
]


# %%
def read_da(fname: str) -> xr.DataArray:
    """
    Read in a data array from disk

    Verifies that the latitude dimension is increasing
    """
    da = xr.load_dataarray(fname)

    # input4MIPs flipped the lat axis compared to the proxies
    da = da.reindex(lat=list(reversed(da.lat)))
    assert da.lat[0] < da.lat[-1]
    return da


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
    source="h2-adjust",
    source_id="CR-historical",
    source_version=__version__,
    target_mip="CMIP",
    grid_label="gn",
)


def check_dims(a: xr.DataArray, b: xr.DataArray, dimensions: Iterable[str]) -> None:
    """
    Check that a subset of dimension of a xarray are consistent

    Parameters
    ----------
    a
        Item A
    b
        Item B
    dimensions
        Dimensions to check
    """
    assert a.shape == b.shape

    for d in dimensions:
        xr.testing.assert_allclose(a[d], b[d])


def write_anthro(slice_filename: str, output_variable: str, title: str) -> None:
    """
    Write an anthropogenic emissions dataset in the Input4MIPs style

    Parameters
    ----------
    slice_filename
        Name of the existing file
    output_variable
        Name of the output variable
    title
        Title of the file

        Added to the files metadata
    """
    example_file = read_da(slice_filename)
    variable_id = f"{output_variable}_em_anthro"

    ds = GriddedEmissionsDataset.create_empty(
        time=example_file.time,
        lat=example_file.lat,
        lon=example_file.lon,
        sectors=SECTOR_MAP,
        version=config.input4mips_archive.version,
        metadata=Input4MIPsMetadata(
            title=title,
            variable_id=variable_id,
            **common_meta,
        ),
    )
    ds.root_data_dir = str(config.input4mips_archive.results_archive)
    ds.data[variable_id].attrs.update(
        {
            "units": "kg m-2 s-1",
            "cell_methods": "time: mean",
            "long_name": f"{output_variable} Anthropogenic Emissions",
        }
    )

    for sector_idx, sector in enumerate(SECTOR_MAP):
        new_data = read_da(slice_filename.replace("Agriculture", sector))

        if new_data is not None:
            check_dims(
                ds.data[variable_id].isel(sector=sector_idx).drop(("sector",)),  # type: ignore
                new_data,
                ("lat", "lon", "time"),
            )
            # This will explode if not lined up correctly
            ds.data[variable_id][:, sector_idx] = new_data[:]

    # These sizes come from the input4MIPs data
    ds.data[variable_id].encoding.update(
        {"chunksizes": {"time": 1, "sector": 4, "lat": 180, "lon": 360}}
    )
    ds.write_slice(ds.data)


def write_anthro_AIR(slice_filename: str, output_variable: str, title: str) -> None:
    """
    Write an aircraft anthropogenic emissions dataset in the Input4MIPs style

    The aircraft files have an additional "levels" dimension

    Parameters
    ----------
    slice_filename
        Name of the existing file
    output_variable
        Name of the output variable
    title
        Title of the file

        Added to the files metadata
    """
    data = read_da(slice_filename)
    variable_id = f"{output_variable}_em_AIR_anthro"

    ds = GriddedAircraftEmissionsDataset.create_empty(
        time=data.time,
        lat=data.lat,
        lon=data.lon,
        levels=LEVELS,
        version=config.input4mips_archive.version,
        metadata=Input4MIPsMetadata(
            title=title,
            variable_id=variable_id,
            **common_meta,
        ),
    )
    ds.root_data_dir = str(config.input4mips_archive.results_archive)
    ds.data[variable_id].attrs.update(
        {
            "units": "kg m-2 s-1",
            "cell_methods": "time: mean",
            "long_name": f"{output_variable} Anthropogenic Emissions",
        }
    )
    del ds.data["level_bounds"]

    updated_data = data.transpose(*ds.dimensions)
    check_dims(
        ds.data[variable_id],
        updated_data,
        ("level", "lat", "lon", "time"),
    )

    ds.data[variable_id][:] = updated_data[:]
    # These sizes come from the input4MIPs data
    ds.data[variable_id].encoding.update(
        {"chunksizes": {"time": 1, "level": 13, "lat": 180, "lon": 360}}
    )
    ds.write_slice(ds.data)


# %%
jobs = []


all_files = config.historical_h2_gridding.output_directory.glob("*.nc")

for slice_filename in sorted(all_files):
    fname = str(slice_filename)
    if "Aircraft" in fname:
        jobs.append(
            (
                write_anthro_AIR,
                fname,
                "H2",
                "Historical anthropogenic aircraft emissions of H2 prepared for CSIRO",
            )
        )
    else:
        jobs.append(
            (
                write_anthro,
                fname,
                "H2",
                "Historical anthropogenic emissions of H2 prepared for CSIRO",
            )
        )
len(jobs)

# %%

# %%
n_jobs = 5
Parallel(n_jobs=n_jobs)(delayed(f)(*args) for f, *args in [jobs[-1]])

# %%
