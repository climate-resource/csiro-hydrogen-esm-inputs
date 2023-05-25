# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags,-pycharm
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
# # Prepare the input data
#
# This notebook does some preprocessing on the masks provided as part of the input data provided by the Feng
# et al 2020 paper to make them easier to use.
#
# This requires that the output from https://zenodo.org/record/2538194 has been downloaded and extracted to
# `<repo_root_dir>/data/raw/emissions_downscaling_archive`.

# %%
import os
import shutil
from glob import glob
from typing import Union

import numpy as np
import pandas as pd
import pyreadr  # type: ignore
import xarray as xr
from joblib import Parallel, delayed  # type: ignore
from numpy.typing import ArrayLike

from local.config import load_config_from_file
from local.pydoit_nb.checklist import generate_directory_checklist

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)


# %%
assert config.gridding_preparation.zenoda_data_archive.is_dir()
assert config.gridding_preparation.zenoda_data_archive.exists()

# %%
# Prepare some variables for running the Rscript
# The trailing "/" are required
script_name = str(config.gridding_preparation.output_rscript)
input_dir = str(config.gridding_preparation.zenoda_data_archive) + "/"
output_dir = str(config.gridding_preparation.output_dir / "seasonality-temp") + "/"

# %%
# split the 4D air seasonality files into n chunks (one per layer)
# This requires that Rscript is available
# !Rscript --vanilla {script_name} {input_dir} {output_dir}

# %%
RAW_GRIDDING_DIR = os.path.join(
    config.gridding_preparation.zenoda_data_archive, "gridding"
)
RAW_GRIDDING_DIR

# %%
GRID_RESOLUTION = 0.5
LAT_CENTERS = np.arange(90 - GRID_RESOLUTION / 2, -90, -GRID_RESOLUTION)
LON_CENTERS = np.arange(
    -180 + GRID_RESOLUTION / 2, 180 + GRID_RESOLUTION / 2, GRID_RESOLUTION
)
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
# Load grid mapping files
grid_mappings = pd.read_csv(
    os.path.join(RAW_GRIDDING_DIR, "gridding-mappings", "country_location_index_05.csv")
).set_index("iso")


# %%
def read_mask_as_da(grid_dir, iso_code, grid_mappings):
    """
    Process a country mask file from and Rd file

    Parameters
    ----------
    grid_dir
        Data folder
    iso_code
        ISO3 country code
    grid_mappings
        Information about the grid by iso code

    Returns
    -------
        Masks for a given country on a lat/lon grid
    """
    iso_code = iso_code.lower()

    fname = f"{grid_dir}/mask/{iso_code}_mask.Rd"
    mask = pyreadr.read_r(fname)[f"{iso_code}_mask"]

    if iso_code in grid_mappings.index:
        mapping = grid_mappings.loc[iso_code]
        lats = LAT_CENTERS[int(mapping.start_row) - 1 : int(mapping.end_row)]
        lons = LON_CENTERS[int(mapping.start_col) - 1 : int(mapping.end_col)]
    else:
        lats = LAT_CENTERS
        lons = LON_CENTERS

    da = xr.DataArray(mask, coords=(lats, lons), dims=("lat", "lon"))

    da.attrs["region"] = iso_code
    da.attrs["source"] = fname
    da.attrs["history"] = f"read_mask_as_da {fname}"
    return da


def read_proxy_file(proxy_fname: str) -> Union[xr.DataArray, None]:
    """
    Read a proxy file from disk

    We are using the existing proxy data from the Feng et al zenodo archive for now.
    These data are stored as Rd files (a proprietary format from R), but can be later
    expanded to also use proxies calculated as part of aneris.

    Parameters
    ----------
    proxy_fname : str
        Path to the proxy data

    Raises
    ------
    FileNotFoundError
        Requested proxy file cannot be found
    Returns
    -------
    xr.DataArray
        Proxy data augmented with latitude and longitude coordinates

    """
    fname = os.path.join(proxy_fname)
    if not os.path.exists(proxy_fname):
        return None

    data = pyreadr.read_r(fname)
    assert len(data) == 1
    data = data[list(data.keys())[0]]

    coords: tuple[ArrayLike, ...]
    dims: tuple[str, ...]
    if data.ndim == 2:  # noqa: PLR2004
        coords, dims = (LAT_CENTERS, LON_CENTERS), ("lat", "lon")
    elif data.ndim == 3 and data.shape[2] != 12:  # noqa: PLR2004
        # AIR data also contain a y dimension
        coords, dims = (LAT_CENTERS, LON_CENTERS, LEVELS), (
            "lat",
            "lon",
            "level",
        )
    elif data.ndim == 3 and data.shape[2] == 12:  # noqa: PLR2004
        # AIR data also contain a y dimension
        coords, dims = (LAT_CENTERS, LON_CENTERS, range(1, 12 + 1)), (
            "lat",
            "lon",
            "month",
        )
    else:
        raise ValueError(f"Unexpected dimensionality for proxy : {data.shape}")  # noqa

    return xr.DataArray(data, coords=coords, dims=dims)  # type: ignore


# %%
output_grid_dir = config.gridding_preparation.output_dir
output_grid_dir

# %% [markdown]
# # Masks

# %%
print("Masks")

fnames = glob(os.path.join(RAW_GRIDDING_DIR, "mask", "*.Rd"))
country_codes = [os.path.basename(f).split("_")[0].upper() for f in fnames]
len(country_codes)

# %%
mask_dir = os.path.join(output_grid_dir, "masks")

if os.path.exists(mask_dir):
    shutil.rmtree(mask_dir)

os.makedirs(mask_dir)


def _read_mask_wrapper(code):
    mask = read_mask_as_da(RAW_GRIDDING_DIR, code, grid_mappings)
    mask.to_netcdf(os.path.join(mask_dir, f"mask_{code.upper()}.nc"))


Parallel(n_jobs=16)(delayed(_read_mask_wrapper)(code) for code in country_codes)

print("Done")

# %% [markdown]
# # Proxies
#
# The proxies are also stored as Rdata
#
# There are 3 folders of interest:
# * proxy-CEDS9
# * proxy-CEDS16
# * proxy-backup

# %%
proxy_dirs = ["proxy-CEDS9", "proxy-CEDS16", "proxy-backup"]


# %%
def write_proxy_file(output_proxy_dir, fname):
    """
    Process a proxy file

    Reads a given proxy file in Rd format into xarray
    and then write out a netcdf file for future use
    """
    proxy = read_proxy_file(fname)
    fname_out, _ = os.path.splitext(os.path.basename(fname))

    toks = fname_out.split("_")
    if len(toks) == 3:  # noqa: PLR2004
        variable, sector, year = toks
    else:
        variable, year = toks
        sector = "Total"

    proxy.attrs["source"] = fname
    proxy.attrs["sector"] = sector
    proxy.attrs["year"] = year

    proxy.to_dataset(name=variable).to_netcdf(
        os.path.join(output_proxy_dir, f"{fname_out}.nc"),
        encoding={variable: {"zlib": True, "complevel": 5}},
    )


for proxy_dir in proxy_dirs:
    print("Proxies " + proxy_dir)
    output_proxy_dir = os.path.join(output_grid_dir, "proxies", proxy_dir)
    if os.path.exists(output_proxy_dir):
        shutil.rmtree(output_proxy_dir)

    os.makedirs(output_proxy_dir)

    fnames = glob(os.path.join(RAW_GRIDDING_DIR, proxy_dir, "*.Rd"))

    Parallel(n_jobs=8)(
        delayed(write_proxy_file)(output_proxy_dir, fname) for fname in fnames
    )

# %%

# Seasonality

print("Seasonality")

output_seasonality_dir = os.path.join(output_grid_dir, "seasonality")
if os.path.exists(output_seasonality_dir):
    shutil.rmtree(output_seasonality_dir)

os.makedirs(output_seasonality_dir)

fnames = glob(os.path.join(RAW_GRIDDING_DIR, "seasonality-CEDS9", "*.Rd"))


def read_seasonality(fname):
    """
    Read a RData file containing seasonality file

    Writes out the read data as a netCDF file for later use

    Parameters
    ----------
    fname
        File to read
    """
    try:
        proxy = read_proxy_file(fname)
    except pyreadr.LibrdataError:
        print(f"failed to read {fname}")
        return

    toks = os.path.basename(fname).split("_")
    proxy.attrs["source"] = fname
    proxy.attrs["sector"] = toks[0]

    if len(toks) == 3:  # noqa: PLR2004
        variable = toks[1]
    else:
        variable = "ALL"
    proxy.attrs["variable"] = variable
    fname_out = f"{toks[0]}_{variable}_seasonality.nc"

    proxy.to_dataset(name=variable).to_netcdf(
        os.path.join(output_seasonality_dir, fname_out),
        encoding={variable: {"zlib": True, "complevel": 5}},
    )


def read_seasonality_chunked(fnames):
    """
    Merge the chunked seasonality files

    The multidimensional R files could not be read in using `pyreadr` instead they
    were chunked into smaller readable files first.

    Parameters
    ----------
    fnames
        List of filename chunks
    """
    fnames = sorted(fnames)
    if not fnames:
        raise FileNotFoundError()

    results = []
    for fname in fnames:
        try:
            proxy = read_proxy_file(fname)
        except pyreadr.LibrdataError:
            print(f"failed to read {fname}")
            return
        results.append(proxy)

    proxy = xr.concat(results, "level").transpose("lat", "lon", "level", "month")

    toks = os.path.basename(fnames[0]).split("_")
    proxy.attrs["sector"] = toks[0]

    variable = toks[1]
    proxy.attrs["variable"] = variable
    fname_out = f"{toks[0]}_{variable}_seasonality.nc"

    proxy.to_dataset(name=variable).to_netcdf(
        os.path.join(output_seasonality_dir, fname_out),
        encoding={variable: {"zlib": True, "complevel": 5}},
    )


Parallel(n_jobs=16)(delayed(read_seasonality)(fname) for fname in fnames)
read_seasonality_chunked(
    glob(
        os.path.join(
            config.gridding_preparation.output_dir,
            "seasonality-temp",
            "AIR_BC_*.Rd",
        )
    )
)
read_seasonality_chunked(
    glob(
        os.path.join(
            config.gridding_preparation.output_dir,
            "seasonality-temp",
            "AIR_NOx_*.Rd",
        )
    )
)

# %%
generate_directory_checklist(output_grid_dir)
