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
# # Extend Timeseries
#
# The first step in the process is extrapolating/resampling the input data to
# annual timeseries.
#
# The input data can hint at what method is used for extrapolation

# %%

from pathlib import Path

import matplotlib.pyplot as plt  # type: ignore
import numpy as np
import numpy.testing as npt
import scmdata

from local.config import load_config_from_file
from local.h2_adjust.constants import HYDROGEN_CARRIERS, HYDROGEN_SECTORS
from local.h2_adjust.timeseries import add_world_region, extend

# %%
plt.rcParams["figure.figsize"] = (12, 8)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%

config = load_config_from_file(config_file)

# %% [markdown]
# # Input scenario
# Extended using growth rates

# %%
# TODO: look at if this is best for emisions
input_scenario = scmdata.ScmRun(config.emissions.input_scenario)
input_scenario

# %%
input_scenario_extended = extend(input_scenario, config.delta_emissions.extensions)

# %%
input_scenario_extended.filter(
    variable="Secondary Energy|*", year=[2020, 2030, 2040, 2050]
).timeseries()

# %%
input_scenario_extended.filter(variable="Secondary Energy|*").lineplot(hue="region")

# %%
input_scenario_extended.filter(variable="Secondary Energy|*").convert_unit(
    "TWh/yr"
).lineplot(hue="region")

# %% [markdown]
# # Share by carriers
# Extend the carrier totals using constant extrapolation. Then infill the sectoral
# breakdown according to the carrier's share. This makes the math easier.
#
#
# The sector breakdown doesn't have to add to 100%
#
# Extended using constant extrapolation. Smarter extrapolation can happen later

# %%
share_by_carrier = scmdata.ScmRun(config.delta_emissions.inputs.share_by_carrier)
share_by_carrier_total = share_by_carrier.filter(sector="Total")
share_by_carrier_sectors = share_by_carrier.filter(sector="Total", keep=False)

# %%
share_by_carrier.timeseries()

# %% [markdown]
# ### Prechecks

# %%
# check that the totals sum to 100
npt.assert_allclose(share_by_carrier_total.timeseries().sum(axis=0), 100, rtol=0)

# %%
# Check the units of the total and sector splits
assert (
    share_by_carrier_total.get_unique_meta("unit", True) == "%"
), "Check units of carrier totals. Should be ''%''"
assert (
    share_by_carrier_sectors.get_unique_meta("unit", True) == "% carrier"
), "Check units of carrier totals. Should be ''% carrier'"


# %%
# Add in missing sectors
def print_missing(ts):
    """
    Print any missings sectors

    The
    """
    for carrier in HYDROGEN_CARRIERS:
        missing_sectors = []

        for sector in HYDROGEN_SECTORS:
            if len(ts.filter(sector=sector, carrier=carrier, log_if_empty=False)) == 0:
                missing_sectors.append(sector)
        if len(missing_sectors):
            print(f"Missing {missing_sectors} for {carrier}")


print_missing(share_by_carrier)

# %% [markdown]
# ### Calculations

# %%
# Extend the carrier totals
# The constant extrapolation preserves the 100% total
share_by_carrier_total_extended = extend(
    share_by_carrier_total, config.delta_emissions.extensions
)

# %%
share_by_carrier_sectors_extended = extend(
    share_by_carrier_sectors, config.delta_emissions.extensions
)

# check that the totals sum to 100
npt.assert_allclose(
    share_by_carrier_total_extended.timeseries().sum(axis=0),
    100,
)
for carrier in share_by_carrier_sectors.get_unique_meta("carrier"):
    npt.assert_allclose(
        share_by_carrier_sectors_extended.filter(carrier=carrier)
        .timeseries()
        .sum(axis=0),
        100,
        err_msg=f"{carrier} sectors do not sum to 100%",
    )

# %%
share_slices = []

for group in share_by_carrier_sectors_extended.groupby("carrier"):
    carrier = group.get_unique_meta("carrier", True)
    print(carrier)
    total = share_by_carrier_total_extended.filter(carrier=carrier)

    # split for carrier in sector CS / T = CS / C * C / T where CS is the amount for the
    # carrier and sector, C is the total for the carrier and T is the total hydrogen
    # (so CS / C is the carrier's share of the total for the carrier and C / T is
    # the carrier's share of all hydrogen)

    calculated_split = group / 100 * total.values.squeeze()
    calculated_split["unit"] = "%"

    share_slices.append(total)
    share_slices.append(calculated_split)

share_by_carrier_extended = scmdata.run_append(share_slices)

# Check that totals still add to 100
npt.assert_allclose(
    share_by_carrier_extended.filter(sector="Total").timeseries().sum(axis=0),
    100,
    rtol=1,
)
# Check that sectors add to 100
npt.assert_allclose(
    share_by_carrier_extended.filter(sector="Total", keep=False)
    .timeseries()
    .sum(axis=0),
    100,
)

share_by_carrier_extended

# %%
# Check that the totals add up

npt.assert_allclose(
    share_by_carrier_extended.filter(region="World", year=2050)
    .filter(sector="Total", keep=False)
    .values.sum(),
    100,
    rtol=0.03,
)

# %%
share_by_carrier_extended.filter(level=1).lineplot(hue="variable")

# %%
share_by_carrier_extended.filter(level=2).lineplot(hue="variable")

# %%
config.delta_emissions.clean.share_by_carrier.parent.mkdir(parents=True, exist_ok=True)
share_by_carrier_extended.to_csv(config.delta_emissions.clean.share_by_carrier)

# %% [markdown]
# # Emissions Intensities


# %%
def process_emissions_intensities(filename: Path) -> scmdata.ScmRun:
    """
    Read and clean an input emissions intensities file

    Parameters
    ----------
    filename
        Path to a file
    Returns
    -------
        A clean emissions intensities dataset
    """
    emissions_intensities = (
        scmdata.ScmRun(filename)
        .set_meta("scenario", config.name)
        .set_meta("model", "h2-adjust")
    )

    emissions_intensities.drop_meta(("comment", "source")).head()

    print_missing(emissions_intensities)

    emissions_intensities_extended = extend(
        emissions_intensities, config.delta_emissions.extensions, method="constant"
    ).filter(unit=np.nan, keep=False)

    return emissions_intensities_extended


def sanitize_intensities(intensities: scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Convert the emissions intensities to a common set of units

    The target unit is "kg X / MWh"
    """
    sanitized_emissions = []

    for product in intensities.get_unique_meta("product"):
        to_clean = intensities.filter(product=product)
        energy_rate = "MWh"
        target_unit = f"kg {product} / {energy_rate}"

        for unit in to_clean.get_unique_meta("unit"):
            selected = to_clean.filter(unit=unit)

            print(unit)
            if not isinstance(unit, str):
                selected["unit"] = target_unit
            else:
                selected = selected.convert_unit(target_unit)

            sanitized_emissions.append(selected)

    return scmdata.run_append(sanitized_emissions)


intensities_combustion = process_emissions_intensities(
    config.delta_emissions.inputs.emissions_intensities_combustion
)

# %%
intensities_combustion.get_unique_meta("unit")

# %%
intensities_combustion_sanitized = sanitize_intensities(intensities_combustion)
config.delta_emissions.clean.emissions_intensities_combustion.parent.mkdir(
    parents=True, exist_ok=True
)
intensities_combustion_sanitized.drop_meta(["comment", "source"]).to_csv(
    config.delta_emissions.clean.emissions_intensities_combustion
)
intensities_combustion_sanitized

# %%
intensities_combustion_sanitized.lineplot(
    hue="sector", style="product", estimator=None, units="variable"
)

# %%
intensities_combustion_sanitized.filter(product="NOx").lineplot(
    hue="sector", style="carrier", estimator=None, units="variable"
)

# %%
intensities_production = process_emissions_intensities(
    config.delta_emissions.inputs.emissions_intensities_production
)
# todo: fix
# intensities_production_sanitized = sanitize_intensities(intensities_production)
config.delta_emissions.clean.emissions_intensities_production.parent.mkdir(
    parents=True, exist_ok=True
)
intensities_production.drop_meta(["comment", "source"]).to_csv(
    config.delta_emissions.clean.emissions_intensities_production
)

# %% [markdown]
# # Energy

# %%
energy_var_name = "Secondary Energy|Hydrogen"
energy_h2 = input_scenario_extended.filter(variable=energy_var_name)

# %%
# Note that bottom up sum of regional Secondary Energy != World Secondary Energy
# Due to Bunkers

bottom_up = energy_h2.filter(region="World", keep=False).process_over(
    "region", "sum", op_cols={"region": "World|Sum"}, as_run=True
)
scmdata.run_append([bottom_up, energy_h2.filter(region="World")]).lineplot(hue="region")

# %%
carriers = ["|".join(v.split("|")[1:]) for v in share_by_carrier["variable"]]
carriers

# %%
carriers = ["|".join(v.split("|")[1:]) for v in share_by_carrier["variable"]]
carriers

# %%
# Check that we have results for each carrier
for c in HYDROGEN_CARRIERS:
    assert c in carriers, c

# %%
energy_h2.timeseries(time_axis="year")

# %%
res = []

for carrier in share_by_carrier_extended.groupby("variable"):
    assert len(carrier) == 1
    energy_by_carrier = energy_h2.timeseries(time_axis="year") * carrier.values / 100
    carrier_name = carrier.get_unique_meta("variable", True)
    carrier_tokens = carrier_name.split("|")
    energy_by_carrier["carrier"] = carrier_tokens[1]
    if len(carrier_tokens) == 3:  # noqa
        energy_by_carrier["sector"] = carrier_tokens[2]
    else:
        energy_by_carrier["sector"] = "Total"
    res.append(scmdata.ScmRun(energy_by_carrier))
energy_by_carrier = add_world_region(scmdata.run_append(res))
energy_by_carrier

# %%
# Add totals

# Only take the top level carriers
total_values = energy_by_carrier.filter(
    carrier=HYDROGEN_CARRIERS, sector="Total"
).process_over("carrier", "sum", op_cols={"carrier": "Total"}, as_run=True)

energy_by_carrier = scmdata.run_append([energy_by_carrier, total_values])
energy_by_carrier

# %%
energy_by_carrier.filter(region="World").filter(carrier="Total", keep=False).filter(
    sector="Total", keep=False
).lineplot(hue="carrier", style="sector")

# %%
energy_by_carrier.filter(carrier="NH3").lineplot(hue="region", style="sector")

# %%
config.delta_emissions.energy_by_carrier.parent.mkdir(parents=True, exist_ok=True)
energy_by_carrier.to_csv(config.delta_emissions.energy_by_carrier)

# %% [markdown]
# # Leakage rates

# %%
leakage_rates = scmdata.ScmRun(config.delta_emissions.inputs.leakage_rates)
leakage_rates.drop_meta(("comment", "source")).head()

# %%
print_missing(leakage_rates)

# %%
leakage_rates_extended = extend(
    leakage_rates, config.delta_emissions.extensions, method="constant"
).filter(unit=np.nan, keep=False)
leakage_rates_extended.drop_meta(("comment", "source")).head()

# %%
leakage_rates_extended.get_unique_meta("unit")

# %%
config.delta_emissions.clean.leakage_rates.parent.mkdir(parents=True, exist_ok=True)
leakage_rates_extended.to_csv(config.delta_emissions.clean.leakage_rates)

# %%
