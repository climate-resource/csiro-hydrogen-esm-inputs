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
# # Calculate delta emissions
#
# The previous notebooks calculated energy by carrier and by region. Here we
# apply the emissions intensity values to the energy from hydrogen production


# %%
import logging

import matplotlib.pyplot as plt  # type: ignore
import pandas as pd
import scmdata

from local.config import load_config_from_file
from local.h2_adjust.units import UNIT_REGISTRY as ur

# %%
logger = logging.getLogger()

# %%
plt.rcParams["figure.figsize"] = (12, 8)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
energy_by_carrier = scmdata.ScmRun(config.delta_emissions.energy_by_carrier)
energy_by_carrier.head()

# %% [markdown]
# # Calculate mass of H2 from energy

# %%
energy_by_carrier.filter(region="World", year=[2050]).timeseries()

# %%
# From first principles:
# Combustion energy of H2 = 286 kJ/mol H2 / 2 g H /mol H2
# 286 kJ / mol H2 = 143 kJ / g H
# = 143 * 1e6 kJ / t H
f_first_principles = 143 * 1e6 * ur("kJ/tH")

# %%
# US DOE quotes 33.3 MWh/tH
# Source: https://www.energy.gov/eere/fuelcells/doe-technical-targets-onboard-hydrogen-storage-light-duty-vehicles
f_doe = 33.3 * ur("MWh/tH")

# %%
# from https://hydrogencouncil.com/wp-content/uploads/2017/11/Hydrogen-Scaling-up_Hydrogen-Council_2017.compressed.pdf
# "1 EJ is provided by 7 million tons or 78 billion cubic meters of gaseous hydrogen"
f_h2_council = 7 * ur("MtH/EJ")


# %%
pd.Series(
    {
        "Heat of Combustion": f_first_principles.to("EJ/MtH"),
        "DOE": f_doe.to("EJ/MtH"),
        "H2 Council": (1 / f_h2_council).to("EJ/MtH"),
    }
)
# %%
# Double check that resulting units are Mt/yr
ur("EJ/yr") * f_h2_council

# %%
# Using the Hydrogen council conversion factor
h2_conversion_factor = f_h2_council


# %% [markdown]
# # Production
#
# All production related emissions are assigned to the industrial sector.


# %%
def process_production_emissions(ts):
    """
    Process the result from a single Emissions intensity timeseries

    All production emissions are associated with the Industrial Sector
    """
    ts = scmdata.ScmRun(ts)
    assert len(ts) == 1
    carrier = ts.get_unique_meta("carrier", True)
    product = ts.get_unique_meta("product", True)

    energy = energy_by_carrier.filter(
        carrier=carrier, sector="Total", log_if_empty=False
    )

    if len(energy) == 0:
        msg = f"No Energy|{carrier} found. Assuming 0"
        raise ValueError(msg)

    production = energy * h2_conversion_factor.m
    production["unit"] = "Mt H/yr"

    product_unit = product if product != "H2" else "H"
    target_unit = f"Mt {product_unit}/yr"

    assert all(energy["year"] == ts["year"])

    if carrier == "NH3":
        production_nh3 = production * 17 / 3
        production_nh3["unit"] = "Mt NH3/yr"
        # Units are all kg/t
        emissions = production_nh3 * ts.values.squeeze() / 1000
    elif carrier == "H2":
        # Units are all %
        assert target_unit == production.get_unique_meta("unit", True)
        emissions = (
            production * ts.values.squeeze() / 100.0
        )  # % are used not dimensionless
    else:
        raise ValueError(f"No production for {product}")  # noqa

    emissions["variable"] = f"Emissions|{product}"
    emissions["unit"] = target_unit
    emissions["product"] = product
    emissions["sector"] = "Industrial Sector"
    emissions["method"] = "Production"

    return emissions


emissions_intensities_production = scmdata.ScmRun(
    config.delta_emissions.clean.emissions_intensities_production
)
emissions_intensities_production.head()

emissions_production = emissions_intensities_production.groupby(
    "variable", "unit", "carrier", "product", "sector"
).apply(process_production_emissions)

emissions_production

# %% [markdown]
# # Combustion

# %%
emissions_intensities_combustion = scmdata.ScmRun(
    config.delta_emissions.clean.emissions_intensities_combustion
)
emissions_intensities_combustion.head()


# %%
def process_combustion_emissions(intensities: scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Process the result from a single Emissions intensity timeseries
    """
    assert len(intensities) == 1
    carrier = intensities.get_unique_meta("carrier", True)
    sector = intensities.get_unique_meta("sector", True)
    product = intensities.get_unique_meta("product", True)
    assert intensities.get_unique_meta("variable", True).startswith(
        "Emissions Intensity|"
    )

    energy = energy_by_carrier.filter(
        carrier=carrier, sector=sector, log_if_empty=False
    )

    if len(energy) == 0:
        msg = f"No Energy|{carrier}|{sector} found. Assuming 0"
        logger.warning(msg)
        return scmdata.ScmRun()

    target_unit = f"Mt {product}/yr"
    unit = ur(intensities.get_unique_meta("unit", True))
    energy_unit = ur(energy.get_unique_meta("unit", True))

    assert all(energy["year"] == intensities["year"])

    print(unit)
    print(unit * energy_unit)
    print(target_unit)

    emissions = energy * intensities.values.squeeze()
    emissions["unit"] = str((unit * energy_unit).u)
    emissions = emissions.convert_unit(target_unit, context="AR6GWP100").drop_meta(
        "unit_context"
    )
    if product == "H":
        product = "H2"
    emissions["variable"] = f"Emissions|{product}"
    emissions["unit"] = target_unit
    emissions["product"] = product
    emissions["method"] = "Combustion"

    return emissions


# %%
emissions_combustion = emissions_intensities_combustion.groupby(
    "variable", "unit", "carrier", "product", "sector"
).apply(process_combustion_emissions)

emissions_combustion

# %%
for variable in emissions_combustion.get_unique_meta("variable"):
    plt.figure()
    plt.title(variable)
    emissions_combustion.filter(variable=variable, region="World").lineplot(
        hue="carrier", style="sector"
    )

# %%
for carrier in emissions_combustion.get_unique_meta("carrier"):
    plt.figure()
    plt.title(carrier)
    emissions_combustion.filter(carrier=carrier, region="World").lineplot(
        hue="variable", style="sector"
    )

# %% [markdown]
# # Fugative Emissions
# Assumed to be global

# %%
leakage_rates = scmdata.ScmRun(config.delta_emissions.clean.leakage_rates)
leakage_rates.head()


# %%
def process_leakage(leakage):
    """
    Process the result from a single leakage timeseries
    """
    leakage = scmdata.ScmRun(leakage)
    assert len(leakage) == 1

    carrier = leakage.get_unique_meta("carrier", True)
    sector = leakage.get_unique_meta("sector", True)
    product = leakage.get_unique_meta("product", True)

    unit = leakage.get_unique_meta("unit", True)
    assert leakage.get_unique_meta("variable", True).startswith("Leakage Rate|")

    if product == "H2":
        product = "H"

    target_unit = f"Mt {product}/yr"

    print(f"{unit} => {target_unit}")

    energy = energy_by_carrier.filter(
        carrier=carrier, sector=sector, log_if_empty=False
    )

    if len(energy) == 0:
        logger.warning(f"No Secondary Energy found for {carrier}|{sector}. Assuming 0")
        return scmdata.ScmRun()

    # Work out unit conversion
    if "%" in unit:
        consumption = energy * h2_conversion_factor.m
        consumption["unit"] = "Mt H/yr"

        if product == "H":
            pass
        elif product == "CH4":
            # Use conservation of mass (1/12 + 4)
            consumption = consumption * 16 / 4
            consumption["unit"] = "Mt CH4/yr"

        elif product == "NH3":
            consumption = consumption * 17 / 3
            consumption["unit"] = "Mt NH3/yr"

        else:
            raise ValueError(f"Don't know how to handle {product}")  # noqa

        assert all(consumption["year"] == leakage["year"])

        emissions = consumption * leakage.values.squeeze() / 100.0
    else:
        unit = ur(unit)
        energy_unit = ur(energy.get_unique_meta("unit", True))

        emissions = energy * leakage.values.squeeze()
        emissions["unit"] = str((unit * energy_unit).u)
        emissions = emissions.convert_unit(target_unit, context="AR6GWP100").drop_meta(
            "unit_context"
        )
    if product == "H":
        product = "H2"
    emissions["variable"] = f"Emissions|{product}"
    emissions["unit"] = target_unit
    emissions["carrier"] = carrier
    emissions["product"] = product
    emissions["method"] = "Leakage"

    return emissions


def run_leakage(ts):
    """
    Process the leakage rates and catch any exceptions
    """
    try:
        return process_leakage(ts)
    except Exception as e:
        print(e)
        return scmdata.ScmRun()


# %%
emissions_leakage = leakage_rates.groupby(
    "variable", "unit", "carrier", "product", "sector"
).apply(run_leakage)

emissions_leakage

# %%
for carrier in emissions_leakage.get_unique_meta("carrier"):
    plt.figure()
    plt.title(carrier)
    emissions_leakage.filter(carrier=carrier, region="World").lineplot(
        hue="variable", style="sector"
    )

# %%
emissions = scmdata.run_append(
    [emissions_combustion, emissions_leakage, emissions_production]
)
emissions

# %%
total_emissions = emissions.process_over(("carrier", "product", "method"), "sum")
total_emissions

# %%
scmdata.ScmRun(total_emissions).process_over(("sector",), "sum", as_run=True).filter(
    variable="Emissions|H2"
).lineplot(hue="region")

# %%
emissions.to_csv(config.delta_emissions.delta_emissions_complete)
total_emissions.to_csv(config.delta_emissions.delta_emissions_totals)

# %%
