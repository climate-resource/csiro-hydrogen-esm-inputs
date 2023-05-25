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
# # Projection gridding
#
# Combine global-mean concentration outputs from MAGICC and gridding information based on methodology used in Meinshausen et al. (2020) to create gridded projections.
#
# This notebook currently includes a redundant harmonisation step, but we should leave that in there as it may be helpful in future work, does not come with significant cognitive overhead given how familiar we all are with harmonisation and is a good guardrail.

# %%
import aneris.convenience  # type: ignore
import cf_xarray.units
import cftime  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import pint_xarray  # type: ignore
import pooch  # type: ignore
import scmdata
import xarray as xr
from carpet_concentrations.gridders import LatitudeSeasonalityGridder
from carpet_concentrations.time import (
    convert_time_to_year_month,
    convert_year_month_to_time,
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

# %%
out_dir = config.concentration_gridding.interim_gridded_output_dir
out_dir.mkdir(parents=True, exist_ok=True)
out_dir

# %%
RCMIP_VAR_MAP = {
    "mole-fraction-of-carbon-dioxide-in-air": "Atmospheric Concentrations|CO2",
    "mole-fraction-of-methane-in-air": "Atmospheric Concentrations|CH4",
}

# %%
SCEN_MAP = {
    # Output name: CMIP6 grid to use
    "CR-ssp119-low": "IMAGE-ssp119",
    "CR-ssp119-med": "IMAGE-ssp119",
    "CR-ssp119-high": "IMAGE-ssp119",
    "CR-ssp226-low": "IMAGE-ssp126",
    "CR-ssp226-med": "IMAGE-ssp126",
    "CR-ssp226-high": "IMAGE-ssp126",
    "CR-ssp245-low": "MESSAGE-GLOBIOM-ssp245",
    "CR-ssp245-med": "MESSAGE-GLOBIOM-ssp245",
    "CR-ssp245-high": "MESSAGE-GLOBIOM-ssp245",
}

# %% [markdown]
# ## Historical concentrations

# %% [markdown]
# We can't update these from CMIP6 because of the need for consistency with model spin up and latitudinal gradients and seasonality.

# %%
hist_concs = pooch.retrieve(
    path=config.rcmip.concentrations_path.parent,
    url="https://rcmip-protocols-au.s3-ap-southeast-2.amazonaws.com/v5.1.0/rcmip-concentrations-annual-means-v5-1-0.csv",
    fname=config.rcmip.concentrations_path.name,
    known_hash="b6749ea32cc36eb0badc5d028b5b7b7bbcc56606144155fa2c0c3f9ceeac18c9",
    progressbar=True,
)
hist_concs = scmdata.ScmRun(hist_concs, lowercase_cols=True).filter(
    region="World",
    scenario=["ssp245"],
    year=range(1, 2015 + 1),
)
hist_concs["scenario"] = "historical"
hist_concs["harmonised"] = "history"
hist_concs

# %%
for v in ["*CH4", "*N2O", "*CO2"]:
    ax = hist_concs.filter(variable=v).lineplot(style="variable")
    ax.grid()
    plt.show()

# %% [markdown]
# ## Projections
#
# Assume we have projections in a format we're happy with too.

# %%
PROJECTIONS_FILE = config.magicc_runs.output_file
projections = scmdata.ScmRun.from_nc(str(PROJECTIONS_FILE))
projections

# %%
pdf = hist_concs.append(projections)
for v in [
    "*CH4",
    "*N2O",
    "*CO2",
    #     "*H2"
]:
    display(  # noqa: F821
        pdf.filter(variable=v, year=range(2010, 2020 + 1)).timeseries()
    )
    ax = pdf.filter(variable=v, year=range(2010, 2030 + 1)).lineplot(style="variable")
    ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
    ax.grid()
    plt.show()

# %% [markdown]
# ## Harmonise

# %%
harmonisation_year = 2015

# %%
harmonised = aneris.convenience.harmonise_all(
    scenarios=projections.timeseries(time_axis="year"),
    history=hist_concs.timeseries(time_axis="year"),
    harmonisation_year=harmonisation_year,
)
harmonised = scmdata.ScmRun(harmonised).filter(year=range(harmonisation_year, 3000))
harmonised["harmonised"] = True
harmonised

# %%
# # %matplotlib notebook
pdf = hist_concs.append(harmonised).append(projections)
v = "*CH4"

ax = pdf.filter(variable=v, year=range(2010, 2100 + 1)).lineplot(style="harmonised")
ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
ax.grid()

# %%
# %matplotlib inline
pdf = hist_concs.append(harmonised)
for v in ["*CH4", "*N2O", "*CO2"]:
    ax = pdf.filter(variable=v, year=range(2010, 2100 + 1)).lineplot(style="harmonised")
    ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
    ax.grid()
    plt.show()


# %% [markdown]
# ## Convert to xarray


# %%
def to_xarray(ts_v: scmdata.ScmRun) -> xr.Dataset:
    """
    Convert to xarray
    """
    units_v = ts_v.get_unique_meta("unit", True)

    ts_xr = (
        ts_v.to_xarray(dimensions=("region", "scenario"), extras=("model",))
        .groupby("time.year")
        .mean()
        .pint.quantify(**{rcmip_variable: units_v})
    )

    return ts_xr


# %% [markdown]
# ## Interpolate onto monthly timestep
#
# Pre-interpolating (with mean preserving interpolation) is really important to avoid unnecesary jumps at boundaries.


# %%
def convert_to_middle_of_year_time(inp):
    """
    Put time on the middle of the year
    """
    return inp.rename({"year": "time"}).assign_coords(
        {"time": [cftime.datetime(y, 7, 1) for y in inp["year"].values]}
    )


# %%
def interpolate_to_monthly(inp):
    """
    Interpolate down to monthly timestep
    """
    # TODO: https://gitlab.com/climate-resource/csiro-planning/-/issues/32
    return inp.interp(
        time=[
            cftime.datetime(y, m, 1)
            for y in inp["time"].dt.year.values
            for m in range(1, 13)
        ],
        kwargs=dict(fill_value="extrapolate"),
    )


# %% [markdown]
# ## Load seasonality and latitudinal gradient

# %%
cmip6_seasonality_lat_grad_file = (
    config.concentration_gridding.cmip6_seasonality_and_latitudinal_gradient_path
)
cmip6_seasonality_lat_grad_file


# %%
def load_dataset_and_add_bounds_units(f: str) -> xr.Dataset:
    """
    Load dataset and add units to bounds

    When writing to disk, xarray strips the
    units of bounds to follow cf conventions
    (see http://cfconventions.org/cf-conventions/cf-conventions.html#cell-boundaries
    and https://github.com/pydata/xarray/issues/2921).
    This function puts the units back on the bounds
    variables so they can be quantified etc.

    The logic follows that in xarray.conventions.cf_encoder

    Parameters
    ----------
    f
        File to load

    Returns
    -------
    Dataset, with units copied to bounds variables from
    the source variable (i.e. the variable which has bounds).
    """
    tmp = xr.load_dataset(f)

    attrs_to_copy = [
        "units",
    ]
    for k in tmp.variables:
        v = tmp[k]

        bounds = v.attrs["bounds"] if "bounds" in v.attrs else None
        if bounds:
            for attr in attrs_to_copy:
                tmp[bounds].attrs[attr] = v.attrs[attr]

    return tmp


# %%
cmip6_seasonality_lat_grad = load_dataset_and_add_bounds_units(
    cmip6_seasonality_lat_grad_file
).pint.quantify()
cmip6_seasonality_lat_grad

# %% [markdown]
# ## Grid

# %%
cmip6_seasonality_lat_grad_scenario_renamed = []
for scen, source_scen in SCEN_MAP.items():
    tmp = cmip6_seasonality_lat_grad.sel(scenario=[source_scen]).copy()
    tmp = tmp.assign_coords(scenario=[scen])
    cmip6_seasonality_lat_grad_scenario_renamed.append(tmp)

cmip6_seasonality_lat_grad_scenario_renamed

# %% [markdown]
# ## Crunch

# %%
for variable in config.cmip6_concentrations.concentration_variables:
    print(f"Processing {variable}")
    print("-" * (len(variable) + 11))
    rcmip_variable = RCMIP_VAR_MAP[variable]
    variable_under = variable.replace("-", "_")

    ts_xr = to_xarray(
        pdf.filter(
            variable=rcmip_variable,
            year=range(2010, 2500 + 1),
            harmonised=True,
        )
    )

    ts_xr_monthly = interpolate_to_monthly(
        convert_to_middle_of_year_time(ts_xr)
    ).pint.quantify(**{rcmip_variable: ts_xr[rcmip_variable].data.units})

    years = range(2040, 2045 + 1)
    ts_xr.sel(year=years, region="World")[rcmip_variable].plot.line(hue="scenario")
    plt.show()
    ts_xr_monthly.sel(time=(ts_xr_monthly.time.dt.year.isin(years)), region="World")[
        rcmip_variable
    ].plot.line(hue="scenario")
    plt.show()

    cmip6_seasonality_lat_grad_scenario_renamed_for_variable = (
        xr.concat(cmip6_seasonality_lat_grad_scenario_renamed, dim="scenario")
        .sel(variable=variable_under)
        .drop("variable")
    )

    res = LatitudeSeasonalityGridder(
        cmip6_seasonality_lat_grad_scenario_renamed_for_variable
    ).calculate(convert_time_to_year_month(ts_xr_monthly))

    res_time_axis = convert_year_month_to_time(res)

    # TODO: make sure this flows through more sensibly
    for v in res_time_axis.data_vars:
        res_time_axis[v].attrs["cell_methods"] = "time: mean area: mean"

    display(res_time_axis)  # noqa: F821

    res_time_axis.sel(region="World").groupby("time.year").mean().mean("lat")[
        rcmip_variable
    ].plot(hue="scenario")
    plt.show()

    res_time_axis.sel(region="World")[rcmip_variable].plot.pcolormesh(
        x="time", y="lat", row="scenario", cmap="rocket_r", levels=100
    )
    plt.show()

    res_time_axis.sel(region="World")[rcmip_variable].plot.contour(
        x="time", y="lat", row="scenario", cmap="rocket_r", levels=30
    )
    plt.show()

    res_time_axis.sel(region="World").sel(lat=[-87.5, 0, 87.5], method="nearest")[
        rcmip_variable
    ].plot.line(hue="lat", row="scenario", alpha=0.4)
    plt.show()

    res_time_axis.sel(region="World").sel(
        lat=[-87.5, 0, 87.5], method="nearest"
    ).groupby("time.year").mean()[rcmip_variable].plot.line(
        hue="lat", row="scenario", alpha=0.4
    )
    plt.show()

    out_file = out_dir / f"{variable}_gridded.nc"
    res_time_axis.drop("model").pint.dequantify().to_netcdf(out_file)
    print(f"{out_file!r}")

# %%
generate_directory_checklist(out_dir)
