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
# # Merge the adjustments with baseline
#
# Delta emissions from 200_calculate_delta_emissions, baseline H2 from
# 201_calculate_anthropogenic_baseline and the remainder of the baseline emissions
# from 000_make_input_files

# %%

import bookshelf  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import scmdata
from matplotlib.backends.backend_pdf import PdfPages  # type: ignore

from local.config import load_config_from_file

plt.rcParams["figure.figsize"] = (12, 8)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%

config = load_config_from_file(config_file)


# %% [markdown]
# # Load data

# %%
delta_emissions = scmdata.ScmRun(config.delta_emissions.delta_emissions_complete)

# %%
input_scenario = scmdata.ScmRun(config.emissions.input_scenario).filter(
    variable="Baseline Emissions|*"
)

baseline_h2 = (
    scmdata.ScmRun(config.projected_h2_emissions.baseline_h2_emissions_regions)
    .filter(type="anthropogenic", year=range(2015, 2101))
    .drop_meta(["type", "sector_short"])
)
baseline_h2["variable"] = baseline_h2["variable"] + "|" + baseline_h2["sector"]
baseline_h2 = baseline_h2


# %% [markdown]
# # Calculate total emissions


# %%
# TODO remove
def _get_sector_from_variable(v):
    return v.split("|")[-1]


# %%
scenario = delta_emissions.get_unique_meta("scenario", True)
model = delta_emissions.get_unique_meta("model", True)
scenario


# %%
_input_data = []

delta_emissions["variable"] = (
    delta_emissions["variable"] + "|" + delta_emissions["sector"]
)
for product in delta_emissions.get_unique_meta("product"):
    context = None
    if "N2O" in product:
        context = "N2O_conversions"
    if "NOx" in product:
        context = "NOx_conversions"

    target_unit = delta_emissions.filter(product=product).get_unique_meta("unit", True)

    if product == "H2":
        baseline = baseline_h2

        # Override attributes to make the add work
        for c in ["assumptions", "model", "scenario"]:
            baseline[c] = input_scenario.get_unique_meta(c, True)
    elif product == "N2O":
        baseline = input_scenario.filter(
            variable=f"Baseline Emissions|{product}"
        ).convert_unit(target_unit, context=context)
        baseline["sector"] = "Total"
        baseline["variable"] = "Emissions|N2O|Total"
    else:
        baseline = input_scenario.filter(
            variable=f"Baseline Emissions|{product}|*", log_if_empty=False
        ).convert_unit(target_unit, context=context)
    baseline["variable"] = baseline["variable"].str.replace("Baseline ", "")
    _input_data.append(baseline)

input_scenario_clean: scmdata.ScmRun = (
    scmdata.run_append(_input_data)
    .resample("AS")
    .filter(year=range(2015, 2101))
    .drop_meta("unit_context")
)
input_scenario_clean["sector"] = input_scenario_clean["variable"].apply(
    _get_sector_from_variable
)
input_scenario_clean["source"] = "baseline"
input_scenario_clean["scenario"] = scenario
input_scenario_clean["model"] = model
input_scenario_clean

# %%
total_delta_emissions = scmdata.ScmRun(
    delta_emissions.process_over(("carrier", "product", "method"), "sum")
)
total_delta_emissions

# %%
n2o_emissions = total_delta_emissions.filter(variable="Emissions|N2O|*").process_over(
    ("sector", "variable"),
    "sum",
    op_cols={"variable": "Emissions|N2O|Total", "sector": "Total"},
    as_run=True,
)
total_delta_emissions = scmdata.run_append(
    [
        total_delta_emissions.filter(variable="Emissions|N2O|*", keep=False),
        n2o_emissions,
    ]
)

# %%
input_scenario_clean.get_unique_meta("unit")

# %%
# Add the deltas where applicable
output_scenario = input_scenario_clean.copy()
output_scenario["modified"] = False

for ts in total_delta_emissions.groupby("variable"):
    variable = ts.get_unique_meta("variable", True)

    existing = output_scenario.filter(variable=variable, log_if_empty=False)
    if len(existing) == 0:
        print(f"No {variable} available. Skipping")
        continue
    existing_unit = existing.get_unique_meta("unit", True)
    new_ts = existing.drop_meta("source").add(
        ts.set_meta("modified", True),
        op_cols={
            "modified": True,
            "unit": existing_unit,
            "scenario": scenario,
            "model": model,
        },
    )

    print(f"Updating {variable}")
    output_scenario = scmdata.run_append(
        [output_scenario.filter(variable=variable, keep=False), new_ts]
    )

output_scenario["source"] = "adjusted"

# %%
# Mark all H2 emissions as modified
output_scenario = output_scenario.set_meta("modified", True, variable="*|H2|*")

# %%
output_scenario.get_unique_meta("unit")

# %%
modified_variables = output_scenario.filter(modified=True).get_unique_meta("variable")
modified_variables

# %%
scmdata.run_append([input_scenario_clean, output_scenario]).filter(
    region="World", variable=modified_variables
).lineplot(hue="variable", style="source")

# %%
scenarios = scmdata.run_append([input_scenario_clean, output_scenario])

# %%
scenarios.to_csv(config.emissions.complete_scenario)

# %% [markdown]
# # Plots

# %%
hue_disagg_method = "carrier"

agg_meta = {"carrier", "sector", "method"}

target_meta = tuple(agg_meta - {hue_disagg_method})


for product in delta_emissions.get_unique_meta("product"):
    plt.figure(figsize=(12, 8))
    added_emissions = scmdata.ScmRun(
        delta_emissions.filter(
            region="World", product=product, log_if_empty=False
        ).process_over(target_meta, "sum")
    )

    scenario_emms = input_scenario_clean.filter(
        variable=f"Emissions|{product}", region="World", log_if_empty=False
    )
    scenario_emms[hue_disagg_method] = "Baseline"

    scmdata.run_append([added_emissions, scenario_emms]).filter(
        region="World"
    ).lineplot(hue=hue_disagg_method)
    plt.title(product)

# %%
hue_disagg_method = "carrier"
style_disagg_method = "sector"

agg_meta = {"carrier", "sector", "method"}

target_meta = tuple(agg_meta - {hue_disagg_method, style_disagg_method})

for product in delta_emissions.get_unique_meta("product"):
    plt.figure(figsize=(12, 8))
    added_emissions = scmdata.ScmRun(
        delta_emissions.filter(
            region="World", product=product, log_if_empty=False
        ).process_over(target_meta, "sum")
    )

    scenario_emms = input_scenario_clean.filter(
        variable=f"Emissions|{product}", region="World", log_if_empty=False
    )
    scenario_emms[hue_disagg_method] = "Baseline"

    scmdata.run_append([added_emissions, scenario_emms]).lineplot(
        hue=hue_disagg_method, style=style_disagg_method
    )
    plt.title(product)

# %%
disagg_method = "method"

agg_meta = {"carrier", "sector", "method"}

target_meta = tuple(agg_meta - {disagg_method})


for product in delta_emissions.get_unique_meta("product"):
    plt.figure(figsize=(12, 8))
    added_emissions = scmdata.ScmRun(
        delta_emissions.filter(
            region="World", product=product, log_if_empty=False
        ).process_over(target_meta, "sum")
    )

    scenario_emms = input_scenario_clean.filter(
        variable=f"Emissions|{product}", region="World", log_if_empty=False
    )
    scenario_emms[hue_disagg_method] = "Baseline"

    scmdata.run_append([added_emissions, scenario_emms]).lineplot(
        hue=disagg_method, style="variable"
    )
    plt.title(product)

# %%
scenarios.filter(variable="Emissions|H2*")

# %%
scenarios.filter(region="World")

unique_units = scenarios.get_unique_meta("unit")

with PdfPages(config.emissions.figure_by_sector) as pdf:
    for u in unique_units:
        plt.figure(figsize=(12, 8))
        scenarios.filter(region="World", unit=u).lineplot(
            hue="variable", style="source"
        )
        pdf.savefig()

# %%
# Only modified

unique_units = scenarios.get_unique_meta("unit")

with PdfPages(config.emissions.figure_by_sector_only_modified) as pdf:
    for u in unique_units:
        plt.figure(figsize=(12, 8))
        scenarios.filter(region="World", variable=modified_variables, unit=u).lineplot(
            hue="variable", style="source"
        )
        pdf.savefig()

# %% [markdown]
#
# # Scenario
#
# Produce a set of emissions that will later be used to run MAGICC.
#
# * World-only
# * Totals (except for CO2), including H2
# * 2015-2100 inclusive

# %%
adjusted_emissions = scenarios.filter(region="World", source="adjusted").drop_meta(
    ["modified", "source"]
)
adjusted_emissions["variable"] = (
    "Emissions|" + adjusted_emissions["variable"].str.split("|").str[1]
)

adjusted_emissions.timeseries()

# %%
total_adjusted_emissions = adjusted_emissions.process_over("sector", "sum", as_run=True)
total_adjusted_emissions.timeseries()

# %%
variables_to_add = [
    "Baseline Emissions|BC",
    "Baseline Emissions|CO",
    "Baseline Emissions|OC",
]

# %%
# Add in other emissions
baseline_emissions = input_scenario.filter(
    variable=[*variables_to_add, "Baseline Emissions|CO2|*"], region="World"
)

co2_afolu = baseline_emissions.filter(variable="Baseline Emissions|CO2|AFOLU").set_meta(
    "variable", "Emissions|CO2|MAGICC AFOLU"
)
co2_fossil = (
    baseline_emissions.filter(variable="Baseline Emissions|CO2|*")
    .filter(variable="Baseline Emissions|CO2|AFOLU", keep=False)
    .process_over(
        "variable",
        "sum",
        as_run=True,
        op_cols={"variable": "Emissions|CO2|MAGICC Fossil and Industrial"},
    )
)

# %%
scenario_for_magicc = (
    scmdata.run_append(
        [
            total_adjusted_emissions,
            baseline_emissions.filter(variable=variables_to_add),
            co2_fossil,
            co2_afolu,
        ]
    )
    .filter(year=range(2015, 2101))
    .convert_unit("kt N2O/yr", variable="Emissions|N2O", context="N2O_conversions")
    .drop_meta("unit_context")
)
scenario_for_magicc["scenario"] = "CR-" + config.name
scenario_for_magicc["variable"] = scenario_for_magicc["variable"].str.replace(
    "Baseline ", ""
)
scenario_for_magicc

# %%
shelf = bookshelf.BookShelf()
rcmip_emissions = (
    shelf.load("rcmip-emissions")
    .timeseries("magicc")
    .filter(scenario="ssp*", region="World", year=range(1900, 2101))
    .filter(scenario=["ssp370-*", "ssp434", "ssp460"], keep=False)
    .filter(variable="Emissions|CO2", keep=False)
    .drop_meta(["activity_id", "mip_era"])
)
rcmip_emissions

# %%
with PdfPages(config.emissions.figure_vs_rcmip) as pdf:
    for v in scenario_for_magicc.get_unique_meta("variable"):
        plt.figure()
        plt.title(v)

        scmdata.run_append([scenario_for_magicc, rcmip_emissions]).filter(
            variable=v
        ).lineplot()
        scenario_for_magicc.filter(variable=v).lineplot(lw=2, legend=False)
        pdf.savefig()

# %%
scenario_for_magicc_complete = scenario_for_magicc.copy()
variables = scenario_for_magicc.get_unique_meta("variable")


for v in rcmip_emissions.get_unique_meta("variable"):
    to_add = rcmip_emissions.filter(
        scenario=config.ssp_scenario, variable=v, year=range(2015, 2101)
    )

    if v not in variables:
        print("adding " + v)
        scenario_for_magicc_complete = scenario_for_magicc_complete.append(to_add)

scenario_for_magicc_complete["scenario"] = "CR-" + config.name
scenario_for_magicc_complete["base_scenario"] = config.ssp_scenario
scenario_for_magicc_complete["assumptions"] = scenario_for_magicc.get_unique_meta(
    "assumptions"
)
scenario_for_magicc_complete

# %%

scenario_for_magicc_complete.resample("AS").timeseries(time_axis="year").to_csv(
    config.emissions.magicc_scenario
)
