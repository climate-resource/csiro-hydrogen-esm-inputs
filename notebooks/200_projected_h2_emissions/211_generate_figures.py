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
# # Generate figures for the paper
#
# Breakdown the generation process into 3 steps. Each Figure has multiple panels that are stitched together
# in Illustrator


# %%
import logging
import warnings

import matplotlib.pyplot as plt  # type: ignore
import scmdata
import seaborn as sns

from local.config import load_config_from_file

# %%
warnings.filterwarnings("ignore")

# %%
logger = logging.getLogger()

# %%
plt.rcParams["figure.figsize"] = (12, 8)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["pdf.use14corefonts"] = True
plt.rcParams["text.usetex"] = False
plt.rcParams["axes.unicode_minus"] = False

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
emissions_delta = scmdata.ScmRun(config.delta_emissions.delta_emissions_complete)
emissions_delta

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


# %%
hue_variable = "carrier"
style_variable = "region"
row_variable = "sector"
col_variable = "product"

hue_order = emissions_delta.get_unique_meta(hue_variable).sort()
style_order = emissions_delta.get_unique_meta(style_variable).sort()
row_order = emissions_delta.get_unique_meta(row_variable).sort()
col_order = emissions_delta.get_unique_meta(col_variable).sort()

line_kwargs = {
    "style": style_variable,
    "hue": hue_variable,
    "hue_order": hue_order,
    "style_order": style_order,
}

facets_kwargs = {
    **line_kwargs,
    "row": row_variable,
    "col": col_variable,
    "row_order": row_order,
    "col_order": col_order,
}

# %% [markdown]
# # Calculate mass of H2 from energy

# %%
fig, axs = plt.subplots(1, 3)

share_by_carrier.filter(sector="Total").lineplot(**line_kwargs, ax=axs[0])

energy_by_carrier.filter(carrier="Total").lineplot(**line_kwargs, ax=axs[1])

energy_by_carrier.filter(
    carrier="Total",
    keep=False,
).filter(
    sector="Total"
).lineplot(**line_kwargs, ax=axs[2])


fig.savefig("figure1_all.pdf")

# %% [markdown]
# # Figure 2
# Ei, f, t, s, g = Gi ,f, t, s x Ff, s, g

# %%
energy_by_carrier.filter(
    carrier="Total",
    keep=False,
).filter(
    sector="Total"
).lineplot(**line_kwargs)

plt.savefig("figure2_a.pdf")

# %%
relplot(share_by_carrier, **{**facets_kwargs, "col": None})
plt.savefig("figure2_b.pdf")


# %%
relplot(
    energy_by_carrier.filter(carrier="Total", keep=False).filter(
        region="World", keep=False
    ),
    **{**facets_kwargs, "col": None}
)
plt.savefig("figure2_c.pdf")

# %% [markdown]
# # Figure 3 - Energy to Emissions

# %%
relplot(
    energy_by_carrier.filter(carrier="Total", keep=False).filter(region="World"),
    **{**facets_kwargs, "col": None}
)
plt.savefig("figure2_a.pdf")

# %%
extra_intensities = (
    scmdata.run_append([leakage_rates, emissions_intensities_production]) / 7
)  # [Mt H / EJ]
extra_intensities["unit"] = "Mt / EJ"

# %%
emissions_intensities_combustion.set_meta("unit", "kg / MWh").convert_unit("Gg / EJ")

# %%
target_unit = "Gg / EJ"

merged_intentsities = scmdata.run_append(
    [
        emissions_intensities_combustion.set_meta("unit", "kg / MWh").convert_unit(
            target_unit
        ),
        extra_intensities.convert_unit(target_unit),
    ]
).process_over(
    ("model", "scenario", "variable"),
    "sum",
    op_cols={"model": None, "scenario": None, "variable": "Emissions Intensity"},
    as_run=True,
)
merged_intentsities.timeseries()

# %%
facets = relplot(merged_intentsities, **facets_kwargs).set(
    yscale="symlog", ylim=[0, 1000]
)

plt.savefig("figure3_b.pdf")

# %%
emissions_delta.process_over("method", "sum", as_run=True).get_unique_meta("carrier")

# %%
relplot(
    emissions_delta.process_over("method", "sum", as_run=True)
    .filter(region="World")
    .set_meta("unit", "Mt/yr")
    .convert_unit("Gg / yr"),
    row=row_variable,
    col=col_variable,
    hue=hue_variable,
    style=style_variable,
).set(yscale="symlog", ylim=[0, 1e5])
plt.savefig("figure3_c.pdf")
