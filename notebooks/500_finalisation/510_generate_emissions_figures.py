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
# # Create figures

# %%
import logging
import os
from pathlib import Path
from typing import Callable

import matplotlib.backends.backend_pdf  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import pandas as pd
import scmdata
import seaborn as sns  # type: ignore

from local.config import Config, load_config_from_file
from local.h2_adjust.constants import PALETTES

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
logging.getLogger("matplotlib.font_manager").disabled = True

# %%
sns.set_theme(
    "talk",
    style="white",
    font_scale=1.01,
    rc={
        "figure.titlesize": "large",
        "legend.fontsize": "medium",
        "legend.title_fontsize": "x-large",
        "axes.labelsize": "medium",
        "ytick.left": True,
        "ytick.direction": "out",
        "ytick.major.size": 5,
        "xtick.bottom": True,
        "xtick.direction": "out",
        "xtick.major.size": 5,
    },
)

# %%
# I don't know why this is needed
plt.figure()

# %%
plt.rcParams["figure.figsize"] = (12, 8)
plt.rcParams["pdf.use14corefonts"] = True
plt.rcParams["text.usetex"] = False
plt.rcParams["axes.unicode_minus"] = False


# %%
merged_dir = config.finalisation_data_dir
merged_dir

# %%
plot_dir = config.finalisation_plot_dir
output_dir = config.finalisation_data_dir

plot_dir.mkdir(exist_ok=True, parents=True)
output_dir.mkdir(exist_ok=True, parents=True)

# %%
input_scenarios = sorted(
    [
        "ssp119-low",
        "ssp119-high",
        "ssp226-low",
        "ssp226-high",
        "ssp245-low",
        "ssp245-high",
    ]
)
input_scenarios

# %%
configs = [
    load_config_from_file(
        str(config.finalisation_notebook_dir.parent.parent / sce / f"{sce}.yaml")
    )
    for sce in input_scenarios
]


# %%
def load_data(configs: list[Config], func: Callable[[Config], Path]):
    """Load a value from each config"""
    ts = []
    for cfg in configs:
        sce_ts = scmdata.ScmRun(func(cfg))

        ts.append(sce_ts)

    ts = scmdata.run_append(ts)
    return ts


# %%
delta_emissions = load_data(
    configs, lambda cfg: cfg.delta_emissions.delta_emissions_complete
)
raw_total_emissions = load_data(configs, lambda cfg: cfg.emissions.complete_scenario)
energy_by_carrier = load_data(
    configs, lambda cfg: cfg.delta_emissions.energy_by_carrier
)


def _split_variable(v):
    tokens = v.split("|")
    assert len(tokens) == 3  # noqa

    return "|".join(tokens[:2])


raw_total_emissions["variable"] = raw_total_emissions["variable"].apply(_split_variable)

# %%
non_total_emissions = raw_total_emissions.filter(sector="Total", keep=False)

total_emissions = scmdata.run_append(
    [
        non_total_emissions,
        non_total_emissions.process_over(
            ("sector", "modified"), "sum", op_cols={"sector": "Total"}, as_run=True
        ),
        raw_total_emissions.filter(sector="Total"),
    ]
)

# %%
total_emissions.get_unique_meta("region")

# %%
delta_emissions.to_csv(os.path.join(output_dir, "emissions_delta.csv"))
total_emissions.to_csv(os.path.join(output_dir, "emissions_total.csv"))
energy_by_carrier.to_csv(os.path.join(output_dir, "energy_by_carrier.csv"))

# %% [markdown]
# # Line chart of total emissions

# %%
scenarios = total_emissions.get_unique_meta("scenario")
scenarios

# %%
products = delta_emissions.get_unique_meta("product")
products

# %%
carriers = delta_emissions.get_unique_meta("carrier")
carriers

# %%
total_emissions["name"] = total_emissions["model"] + " " + total_emissions["scenario"]
delta_emissions["name"] = delta_emissions["model"] + " " + delta_emissions["scenario"]
energy_by_carrier["name"] = (
    energy_by_carrier["model"] + " " + energy_by_carrier["scenario"]
)
total_emissions.get_unique_meta("name")

# %%
total_emissions

# %%
styles = {"adjusted": "-", "baseline": "--"}

pdf = matplotlib.backends.backend_pdf.PdfPages(
    os.path.join(plot_dir, "total_emissions.pdf")
)


for product in products:
    fig = plt.figure()
    plt.title(product)
    sns.despine()

    to_plot = total_emissions.filter(
        variable=f"Emissions|{product}", region="World", sector="Total"
    )

    plt.ylabel(f"Mt {product} / yr")
    plt.xlabel("Year")
    to_plot.lineplot(
        hue="name",
        style="source",
        style_order=["adjusted", "baseline"],
        alpha=0.8,
        lw=2,
        palette=PALETTES["scenarios"],
        estimator=None,
        units="assumptions",
    )

    for values in to_plot.filter(source="adjusted").groupby("name"):
        if len(values) == 1:
            continue
        plt.fill_between(
            values["time"],
            values.values[0],
            values.values[1],
            color=PALETTES["scenarios"][values.get_unique_meta("name", True)],
            alpha=0.2,
        )
    plt.ylim(bottom=0)
    pdf.savefig(fig, transparent=True)
pdf.close()

# %% [markdown]
# # Bar chart of delta emissions

# %%
years = [2030, 2050, 2100]

# %%
delta_emissions.filter(
    variable="Emissions|NOx*",
    region="World",
    assumptions="high",
    method="Combustion",
    sector="Energy Sector",
)


# %%
def get_melted_emissions(data, cols_to_sum=None):
    """Prepare emissions for the bar chart by removing unneeded dimensions"""
    if cols_to_sum:
        data = scmdata.ScmRun(data.process_over(cols_to_sum, "sum"))
    emms_to_plot = data.timeseries(time_axis="year")

    emms_to_plot_melted = pd.melt(emms_to_plot, ignore_index=False).reset_index()
    emms_to_plot_melted["name"] = (
        emms_to_plot_melted["model"] + " " + emms_to_plot_melted["scenario"]
    )

    return emms_to_plot_melted


def make_bar_chart(fig_data, disagg_by, title, units, y=None, **kwargs):
    """Plot a bar chart"""
    fig, axs = plt.subplots(1, len(scenarios), sharey=True)

    fig.suptitle(title)
    names = fig_data["name"].unique()

    for i, (ax, name) in enumerate(zip(axs, names)):
        ax_data = fig_data[fig_data["name"] == name]

        d = ax_data.set_index(["time", disagg_by])["value"].unstack(disagg_by)

        if y is not None:
            y = [i for i in y if i in d.columns]

        d.plot.bar(ax=ax, stacked=True, rot=0, y=y, **kwargs)

        if i == 0:
            sns.despine(ax=ax)
            ax.set_ylabel(units)
        else:
            sns.despine(ax=ax, left=True)
            ax.legend([], [], frameon=False)
            ax.set_ylabel("")
            ax.tick_params(axis="y", which="major", length=0)

        ax.set_xlabel(name)
    plt.tight_layout()

    return fig


# %%
delta_emissions.get_unique_meta("scenario")

# %%
disagg_by = "carrier"
data_to_plot = get_melted_emissions(
    delta_emissions.filter(year=years, region="World", assumptions="low").filter(
        sector="Total", keep=False
    ),
    ["sector", "method"],
)

pdf = matplotlib.backends.backend_pdf.PdfPages(
    os.path.join(plot_dir, "emissions_by_carrier.pdf")
)

for product in products:
    fig = make_bar_chart(
        data_to_plot[data_to_plot["product"] == product],
        disagg_by=disagg_by,
        title=product,
        units=f"Mt {product} / yr",
        color=PALETTES["carriers"],
        y=list(PALETTES["carriers"].keys()),
    )

    pdf.savefig(fig, transparent=True)
pdf.close()


# %%
disagg_by = "region"
data_to_plot = get_melted_emissions(
    delta_emissions.filter(year=years, assumptions="low")
    .filter(region="World", keep=False)
    .filter(sector="Total", keep=False),
    ["carrier", "sector", "method"],
)

pdf = matplotlib.backends.backend_pdf.PdfPages(
    os.path.join(plot_dir, "emissions_by_region.pdf")
)

for product in products:
    fig = make_bar_chart(
        data_to_plot[data_to_plot["product"] == product],
        disagg_by=disagg_by,
        title=product,
        units=f"Mt {product} / yr",
        color=PALETTES["regions"],
        y=list(PALETTES["regions"].keys()),
    )

    pdf.savefig(fig, transparent=True)
pdf.close()


# %%
disagg_by = "sector"
data_to_plot = get_melted_emissions(
    delta_emissions.filter(year=years, region="World", assumptions="low").filter(
        sector="Total", keep=False
    ),
    ["carrier", "method"],
)
y = delta_emissions.get_unique_meta(disagg_by)

pdf = matplotlib.backends.backend_pdf.PdfPages(
    os.path.join(plot_dir, "emissions_by_sector.pdf")
)

for product in products:
    fig = make_bar_chart(
        data_to_plot[data_to_plot["product"] == product],
        disagg_by=disagg_by,
        title=product,
        units=f"Mt {product} / yr",
        y=y,
    )

    pdf.savefig(fig, transparent=True)
pdf.close()

# %% [markdown]
# # Energy by carriers

# %%
energy_by_carrier.filter(region="World", sector="Total", year=range(2015, 2101)).filter(
    carrier="Total"
).timeseries()

# %%
energy_by_carrier.filter(region="World", sector="Total", year=range(2015, 2101)).filter(
    carrier="Total", keep=False
).lineplot(hue="carrier", style="name", palette=PALETTES["carriers"])
sns.despine()
plt.savefig(os.path.join(plot_dir, "energy_by_carrier.pdf"))

# %%
energy_by_carrier.filter(
    sector="Total", year=range(2015, 2101), carrier="Total", assumptions="low"
).filter(region="World", keep=False).lineplot(hue="scenario", style="region")
sns.despine()
plt.savefig(os.path.join(plot_dir, "energy_by_region.pdf"))

# %%
disagg_by = "region"
data_to_plot = energy_by_carrier.filter(
    year=years, assumptions="low", sector="Total", carrier="Total"
).filter(region="World", keep=False)

data_to_plot = get_melted_emissions(data_to_plot)

fig = make_bar_chart(
    data_to_plot,
    disagg_by=disagg_by,
    title="Secondary Energy by region",
    units="EJ / yr",
    color=PALETTES["regions"],
)
plt.savefig(os.path.join(plot_dir, "energy_by_region.pdf"))

# %%
fig, axes = plt.subplots(3, 3, figsize=(10, 10))


for j, year in enumerate(years):
    axes[0, j].set_title(year, y=1.04)
    for i, name in enumerate(data_to_plot.name.unique()):
        ax = axes[i, j]
        d = (
            data_to_plot[(data_to_plot.name == name) & (data_to_plot.time == year)]
            .set_index("region")
            .sort_index()
        )
        colors = [PALETTES["regions"][i] for i in d.index.values]

        if d.value.sum():
            artists = ax.pie(
                d["value"],
                autopct="%.0f%%",
                colors=colors,
                pctdistance=1.2,
            )
        if j == 0:
            ax.set(
                ylabel=name,
                aspect="equal",
            )
            ax.yaxis.set_label_coords(-0.07, 0.5)
plt.tight_layout()
fig.legend(artists[0], d.index, bbox_to_anchor=(0, 0.5))


# %%
