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
import scmdata
import seaborn as sns

from local.config import load_config_from_file

# %%
logger = logging.getLogger()

# %%
plt.rcParams["figure.figsize"] = (12, 8)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
# Load factors/shares

share_by_carrier = scmdata.ScmRun(config.delta_emissions.clean.share_by_carrier)
leakage_rates = scmdata.ScmRun(config.delta_emissions.clean.leakage_rates)
emissions_intensities_production = scmdata.ScmRun(
    config.delta_emissions.clean.emissions_intensities_production
)
emissions_intensities_combustion = scmdata.ScmRun(
    config.delta_emissions.clean.emissions_intensities_combustion
)

# %%
energy_by_carrier = scmdata.ScmRun(config.delta_emissions.energy_by_carrier)
energy_by_carrier.head()


# %%
def relplot(run: scmdata.ScmRun, **kwargs):
    """
    Allow for faceted line plots, with rows and cols

    This functionality is similar to `ScmRun.lineplot`
    """
    long_data = run.long_data(time_axis="year")

    facets = sns.relplot(data=long_data, kind="line", x="time", y="value", **kwargs)

    try:
        unit = run.get_unique_meta("unit", no_duplicates=True)
        facets.set_ylabels(unit)
    except ValueError:
        pass  # don't set ylabel

    return facets


# %% [markdown]
# # Calculate mass of H2 from energy

# %%
share_by_carrier.filter(sector="Total").lineplot(style="variable")


# %%
energy_by_carrier.filter(carrier="Total").lineplot(hue="region")

# %%
energy_by_carrier.filter(
    carrier="Total",
    keep=False,
).filter(
    sector="Total"
).lineplot(hue="region", style="carrier")

# %% [markdown]
# # Figure 2
# Ei, f, t, s, g = Gi ,f, t, s x Ff, s, g

# %%
energy_by_carrier.filter(
    carrier="Total",
    keep=False,
).filter(
    sector="Total"
).lineplot(hue="region", style="carrier")

# %%
relplot(
    share_by_carrier.filter(sector="Total", keep=False), row="sector", style="carrier"
)


# %%
relplot(
    energy_by_carrier.filter(carrier="Total", sector="Total", keep=False),
    row="sector",
    hue="region",
    style="carrier",
)

# %% [markdown]
# # Figure 3 - Energy to Emissions

# %%
relplot(
    energy_by_carrier.filter(carrier="Total", keep=False).filter(
        sector="Total", keep=False
    ),
    row="sector",
    hue="region",
    style="carrier",
)

# %%
relplot(
    emissions_intensities_combustion,
    row="sector",
    col="product",
    hue="region",
    style="carrier",
)

# %%
emissions_intensities_combustion.filter(carrier="H2", product="NOx")

# %%
relplot(
    emissions_intensities_production,
    row="sector",
    col="product",
    hue="region",
    style="carrier",
)

# %%
