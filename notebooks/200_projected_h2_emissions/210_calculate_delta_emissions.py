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
warn_or_raise = "raise"

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
# Calculate the production of H2 from secondary energy
# Assumes no-losses
production_h2 = energy_by_carrier * h2_conversion_factor.m
production_h2["unit"] = "Mt H/yr"
production_h2["variable"] = "Production|H2"


def _maybe_raise(msg):
    if warn_or_raise == "warn":
        logger.warning(msg)
        return scmdata.ScmRun()
    raise ValueError(msg)


def process_production_emissions(production_intensity: scmdata.ScmRun):
    """
    Process the result from a single Emissions intensity timeseries

    All production emissions are associated with the Industrial Sector
    """
    assert len(production_intensity) == 1
    carrier = production_intensity.get_unique_meta("carrier", True)
    product = production_intensity.get_unique_meta("product", True)

    production_carrier = production_h2.filter(
        carrier=carrier, sector="Total", log_if_empty=False
    )

    if len(production_carrier) == 0:
        _maybe_raise(f"No Production|H2 found for carrier {carrier}")

    product_unit = product if product != "H2" else "H"
    target_unit = f"Mt {product_unit}/yr"

    # Checks
    assert f"kg {product} / kg H2" == production_intensity.get_unique_meta("unit", True)

    # Mt H / yr * (kg product / kg H) * (1e9 Mt product/ kg product) * (1/E9 kg H / Mt H) => Mt product / yr
    emissions_carrier = production_carrier * production_intensity.values.squeeze()

    emissions_carrier["variable"] = f"Emissions|{product}"
    emissions_carrier["unit"] = target_unit
    emissions_carrier["product"] = product
    # All production emissions are associated with the industrial sector
    emissions_carrier["sector"] = "Industrial Sector"
    emissions_carrier["method"] = "Production"

    return emissions_carrier


emissions_intensities_production = scmdata.ScmRun(
    config.delta_emissions.clean.emissions_intensities_production
)
emissions_intensities_production.head()

emissions_production = emissions_intensities_production.apply(
    process_production_emissions
)

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
        _maybe_raise(f"No Energy|{carrier}|{sector} found")

    product_unit = product if product != "H2" else "H"
    target_unit = f"Mt {product_unit}/yr"
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
    emissions["variable"] = f"Emissions|{product}"
    emissions["unit"] = target_unit
    emissions["product"] = product
    emissions["method"] = "Combustion"

    return emissions


# %%
emissions_combustion = emissions_intensities_combustion.apply(
    process_combustion_emissions
)
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
# # Fugitive Emissions
# Assumed to be global

# %%
leakage_rates = scmdata.ScmRun(config.delta_emissions.clean.leakage_rates)
leakage_rates.head()


# %%
def process_leakage(leakage):
    """
    Process the result from a single leakage timeseries
    """
    assert len(leakage) == 1

    carrier = leakage.get_unique_meta("carrier", True)
    sector = leakage.get_unique_meta("sector", True)
    product = leakage.get_unique_meta("product", True)

    product_unit = product if product != "H2" else "H"
    target_unit = f"Mt {product_unit}/yr"

    # Sanity checks
    unit = leakage.get_unique_meta("unit", True)
    assert unit == f"kg {product_unit} / kg H"
    assert leakage.get_unique_meta("variable", True).startswith("Leakage Rate|")

    production_carrier_sector = production_h2.filter(
        carrier=carrier, sector=sector, log_if_empty=False
    )

    if len(production_carrier_sector) == 0:
        _maybe_raise(f"No Production|H2 found for {carrier}|{sector}")

    # Mt H / yr * (kg product / kg H) * (1e9 Mt product/ kg product) * (1/E9 kg H / Mt H) => Mt product / yr
    emissions_carrier_sector = production_carrier_sector * leakage.values.squeeze()

    emissions_carrier_sector["variable"] = f"Emissions|{product}"
    emissions_carrier_sector["unit"] = target_unit
    emissions_carrier_sector["carrier"] = carrier
    emissions_carrier_sector["product"] = product
    emissions_carrier_sector["method"] = "Leakage"

    return emissions_carrier_sector


# %%
emissions_leakage = leakage_rates.apply(process_leakage)
emissions_leakage

# %%
for carrier in emissions_leakage.get_unique_meta("carrier"):
    plt.figure()
    plt.title(carrier)
    emissions_leakage.filter(carrier=carrier, region="World").lineplot(
        hue="variable", style="sector"
    )

# %%
merged_emissions = scmdata.run_append(
    [emissions_combustion, emissions_leakage, emissions_production]
)
merged_emissions

# %%
total_emissions = merged_emissions.process_over(("carrier", "product", "method"), "sum")
total_emissions

# %%
scmdata.ScmRun(total_emissions).process_over(("sector",), "sum", as_run=True).filter(
    variable="Emissions|H2"
).lineplot(hue="region")

# %%
merged_emissions.to_csv(config.delta_emissions.delta_emissions_complete)
total_emissions.to_csv(config.delta_emissions.delta_emissions_totals)

# %%
