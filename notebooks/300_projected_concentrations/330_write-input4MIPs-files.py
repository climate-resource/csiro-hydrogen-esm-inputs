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
# # Writing input4MIPs files
#
# Write files in the format required by input4MIPs.

# %%
import copy

import cf_xarray.units
import matplotlib.pyplot as plt
import numpy as np
import pint_xarray
import tqdm.autonotebook as tqdman
import xarray as xr
from carpet_concentrations.input4MIPs.dataset import (
    Input4MIPsDataset,
    Input4MIPsMetadata,
    Input4MIPsMetadataOptional,
)
from carpet_concentrations.xarray_utils import (
    calculate_weighted_area_mean_latitude_only,
)

from local.config import load_config_from_file
from local.pydoit_nb.checklist import generate_directory_checklist

# %%
cf_xarray.units.units.define("ppm = 1 / 1000000")
cf_xarray.units.units.define("ppb = ppm / 1000")

# %%
pint_xarray.accessors.default_registry = pint_xarray.setup_registry(
    cf_xarray.units.units
)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %% [markdown]
# ## Write files
#
# Write files from our own data.

# %%
output_dir = config.concentration_gridding.gridded_output_dir
output_dir

# %%
input_dir = config.concentration_gridding.interim_gridded_output_dir
input_files = list(input_dir.glob("*.nc"))
input_files

# %%
# This is a map from CMIP to RCMIP conventions
rcmip_to_cmip_variable_renaming = {
    "Atmospheric Concentrations|CO2": "mole_fraction_of_carbon_dioxide_in_air",
    "Atmospheric Concentrations|CH4": "mole_fraction_of_methane_in_air",
}


# %%
def convert_to_cmip_conventions(inp):
    """
    Convert to CMIP conventions
    """
    out = inp.copy()
    for k, v in rcmip_to_cmip_variable_renaming.items():
        if k in inp.data_vars:
            #             # not sure if this is needed or not, was in some of the
            #             # CMIP6 files...
            #             out[k].attrs["long_name"] = "mole"
            out = out.rename_vars({k: rcmip_to_cmip_variable_renaming[k]})

    assert all([v in rcmip_to_cmip_variable_renaming.values() for v in out.data_vars])

    return out


# %%
ds = xr.merge(
    [xr.load_dataset(f, use_cftime=True).pint.quantify() for f in input_files]
)
ds = convert_to_cmip_conventions(ds)

ds["lat"].attrs["units"] = "degrees_north"

ds

# %%
v = "mole_fraction_of_carbon_dioxide_in_air"

ds.sel(lat=[-67.5, 67.5], region="World")[v].plot(hue="lat")
plt.show()

lat_mean = calculate_weighted_area_mean_latitude_only(
    ds.cf.add_bounds("lat").pint.quantify({"lat_bounds": "degrees_north"}), [v]
)
lat_mean.sel(region="World")[v].isel(time=range(150)).plot(hue="scenario")
plt.show()

# %%
source_version = "0.1.0"

metadata_self = Input4MIPsMetadata(
    contact="zebedee.nicholls@climate-resource.com",
    dataset_category="GHGConcentrations",
    frequency="mon",
    further_info_url="TBD",  # TODO: point to website or paper or something
    grid_label="{grid_label}",  # TODO: check this against controlled vocabulary
    institution="Climate Resource, Northcote, Victoria [TODO postcode], Australia [TODO check if this should be CSIRO instead]",
    institution_id="CR",
    nominal_resolution="{nominal_resolution}",
    realm="atmos",
    source_id="{scenario}",
    source_version=source_version,
    target_mip="HydrogenMIP",  # TODO: check desired value here
    title="{equal-to-source_id}",
    Conventions="CF-1.6",
    activity_id="input4MIPs",
    mip_era="CMIP6",
    source=f"CR {source_version}",
)

metadata_self

# %%
optional_metadata_self = Input4MIPsMetadataOptional(
    comment="Data produced by Climate Resource for CSIRO as part of [details]",
    grid=(
        "15x360 degree latitude x longitude. Post-processed based on output from "
        "MAGICCv7.5.3 as used in AR6 WG1 ([TODO refs]) and latitudinal and "
        "seasonal information from historical observations (see "
        "Meinshausen et al., 2017 and Meinshausen et al., 2019 for details [TODO double check refs])"
    ),
    product="Projections of greenhouse gas concentrations",  # TODO: specify GHG and scenario
    references="[TODO]",
)
optional_metadata_self


# %%
def get_gmnhsh_data(inp, variables, output_spatial_dim_name="sector", **kwargs):
    """
    Get global-mean and hemispheric data
    """
    gm = (
        calculate_weighted_area_mean_latitude_only(inp, [data_var], **kwargs)
        .expand_dims({output_spatial_dim_name: [0]})
        .drop(["lat_bounds", "lat"])
    )

    nh = inp["lat"] >= 0

    nhm = (
        calculate_weighted_area_mean_latitude_only(
            inp.loc[{"lat": nh}], [data_var], **kwargs
        )
        .expand_dims(dim={output_spatial_dim_name: [1]})
        .drop(["lat_bounds", "lat"])
    )

    shm = (
        calculate_weighted_area_mean_latitude_only(
            inp.loc[{"lat": ~nh}], [data_var], **kwargs
        )
        .expand_dims({output_spatial_dim_name: [2]})
        .drop(["lat_bounds", "lat"])
    )

    out = xr.concat([gm, nhm, shm], dim=output_spatial_dim_name).cf.add_bounds(
        output_spatial_dim_name
    )

    for v in variables:
        out[v].attrs.update(inp[v].attrs)

    out[output_spatial_dim_name].attrs.update(
        {
            "long_name": "sector",
            "ids": "0: Global; 1: Northern Hemisphere; 2: Southern Hemisphere",
            "lat_bounds": "0: -90.0, 90.0; 1: 0.0, 90.0; 2: -90.0, 0.0",
        }
    )

    return out


# %%
def fill_out_metadata(data, scenario, metadata, optional_metadata):
    """
    Fill out placeholders in metadata
    """
    grid_label, nominal_resolution = get_grid_label_nominal_resolution(data)

    metadata.source_id = metadata.source_id.format(scenario=scenario)
    metadata.title = metadata.source_id
    metadata.grid_label = metadata.grid_label.format(grid_label=grid_label)
    metadata.nominal_resolution = metadata.nominal_resolution.format(
        nominal_resolution=nominal_resolution
    )

    check_nothing_unset(metadata)
    check_nothing_unset(optional_metadata)

    return metadata, optional_metadata


# %%
def check_nothing_unset(m):
    """
    Check we haven't left any metadata unset
    """
    unformatted_keys = [k for k, v in m.to_dataset_attributes().items() if "{" in v]
    assert not any(unformatted_keys), unformatted_keys


def lat_fifteen_deg(inp):
    """
    Check if latitude is a 15 degree grid
    """
    return np.allclose(
        inp.lat.values,
        np.array(
            [-82.5, -67.5, -52.5, -37.5, -22.5, -7.5, 7.5, 22.5, 37.5, 52.5, 67.5, 82.5]
        ),
    )


def get_grid_label_nominal_resolution(inp):
    """
    Get grid label and nominal resolution
    """
    dims = inp.dims

    grid_label = None
    nominal_resolution = None
    if "lon" not in dims:
        if "lat" in dims:
            if lat_fifteen_deg(inp) and list(dims) == ["lat", "time"]:
                grid_label = "gn-15x360deg"
                nominal_resolution = "2500km"

        elif "sector" in dims:
            # TODO: more stable handling of dims and whether bounds
            # have already been added or not
            if inp["sector"].size == 3 and list(sorted(dims)) == [  # noqa: PLR2004
                "bounds",
                "sector",
                "time",
            ]:
                grid_label = "gr1-GMNHSH"
                nominal_resolution = "10000 km"

    if any([v is None for v in [grid_label, nominal_resolution]]):
        raise NotImplementedError(  # noqa: TRY003
            f"Could not determine grid_label for data: {inp}"
        )

    return grid_label, nominal_resolution


# %%
# TODO: wrap all this in a factory?
dimensions = ("time", "lat")
dimensions_gmnhsh = ("time", "sector")

for data_var in tqdman.tqdm(ds.data_vars, desc="variable", leave=True):
    dsv = ds[[data_var]].sel(time=ds.time.dt.year.isin(range(2015, 2100 + 1)))

    for scenario, dsvs in tqdman.tqdm(
        dsv.sel(region="World").groupby("scenario", squeeze=True),
        desc="scenario",
        leave=False,
    ):
        metadata, optional_metadata = fill_out_metadata(
            dsvs,
            scenario.replace("_", "-"),
            copy.deepcopy(metadata_self),
            copy.deepcopy(optional_metadata_self),
        )

        drop_coords = set(dsvs.coords) - set(dimensions)
        input4mips_ds = Input4MIPsDataset.from_metadata_autoadd_bounds_to_dimensions(
            dsvs.drop(drop_coords).copy().transpose(*dimensions),
            dimensions,
            metadata=metadata,
            metadata_optional=optional_metadata,
        )
        gridded_path = input4mips_ds.write(root_data_dir=output_dir)
        display(gridded_path)  # noqa: F821

        bounded_data_quantified = input4mips_ds.ds.pint.quantify(
            lat_bounds="degrees_north", lat="degrees_north"
        )
        gmnhsh_data = get_gmnhsh_data(bounded_data_quantified, [data_var])

        metadata_gmnhsh, optional_metadata_gmnhsh = fill_out_metadata(
            gmnhsh_data,
            scenario.replace("_", "-"),
            copy.deepcopy(metadata_self),
            copy.deepcopy(optional_metadata_self),
        )
        gmnhsh_data.attrs["variable_id"] = data_var
        gmnhsh_data.attrs.update(optional_metadata_gmnhsh.to_dataset_attributes())
        gmnhsh_data.attrs.update(metadata_gmnhsh.to_dataset_attributes())

        input4mips_gmnhsh_ds = Input4MIPsDataset(
            gmnhsh_data,
        )
        gmnhsh_path = input4mips_gmnhsh_ds.write(root_data_dir=output_dir)
        display(gmnhsh_path)  # noqa: F821
#         break
#     break

# %%
xr.load_dataset(
    gridded_path,
    use_cftime=True,
)

# %%
xr.load_dataset(
    gmnhsh_path,
    use_cftime=True,
)

# %%
generate_directory_checklist(output_dir)

# %%
# # This can all be deleted in a follow up MR
# from netCDF4 import Dataset
# from difflib import Differ
# from pprint import pprint


# gmnhsh_path_previous_iter = os.path.join(
#     "../../../global-emissions/data/input4MIPs/CMIP6/ScenarioMIP/CR/CR-IMAGE-ssp119-low/atmos/mon/mole-fraction-of-methane-in-air/gr1-GMNHSH/v20221025/mole-fraction-of-methane-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_CR-IMAGE-ssp119-low_gr1-GMNHSH_201501-250012.nc"
# )

# gridded_path_previous_iter = os.path.join(
#     "../../../global-emissions/data/input4MIPs/CMIP6/ScenarioMIP/CR/CR-IMAGE-ssp119-low/atmos/mon/mole-fraction-of-methane-in-air/gn-15x360deg/v20221025/mole-fraction-of-methane-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_CR-IMAGE-ssp119-low_gn-15x360deg_201501-250012.nc"
# )

# for written_file, compare_file in (
#     (gmnhsh_path, gmnhsh_path_previous_iter),
#     (gridded_path, gridded_path_previous_iter),
# ):
#     print(written_file)
#     print("=" * len(written_file.name))
#     nc_dat_written = Dataset(written_file)
#     nc_data_previous = Dataset(compare_file)

#     d = Differ()

#     written_root = sorted(str(nc_dat_written).splitlines(keepends=True))
#     prev_root = sorted(str(nc_data_previous).splitlines(keepends=True))
#     result = list(d.compare(prev_root, written_root))
#     pprint(result)

#     for v in nc_dat_written.variables:
#         print(v)
#         print("-" * len(v))
#         written_v = sorted(str(nc_dat_written[v]).splitlines(keepends=True))
#         try:
#             prev_v = sorted(str(nc_data_previous[v]).splitlines(keepends=True))
#         except:
#             print(f"{v} not included previously")
#             continue

#         result = list(d.compare(prev_v, written_v))
#         pprint(result)
#         print("-" * len(v))
#     print("=" * len(written_file.name))
