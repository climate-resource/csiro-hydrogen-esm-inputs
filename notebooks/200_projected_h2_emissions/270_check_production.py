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
# %%

import matplotlib.pyplot as plt  # type: ignore
import scmdata

from local.config import load_config_from_file

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
delta_emissions = scmdata.ScmRun(config.delta_emissions.delta_emissions_complete)
country_emissions = scmdata.ScmRun(config.emissions.complete_scenario_countries)

# %%
production_emissions = delta_emissions.filter(method="Production", region="World")
production_emissions

# %%
production_emissions.lineplot(hue="variable")

# %%
emissions_country = (
    country_emissions.filter(
        variable="*|Industrial Sector", downscaling="intensity_convergence"
    )
    .drop_meta(["downscaling", "harmonisation", "sector", "source", "modified"])
    .convert_unit("kt H2/yr", variable="Emissions|H2*")
)
emissions_country.timeseries()

# %%
global_totals = emissions_country.process_over(
    "region", "sum", op_cols={"region": "World"}, as_run=True
)

# %%
aus_emissions = emissions_country.filter(region="AUS")
aus_emissions

# %%
aus_portion = aus_emissions.divide(global_totals, {"region": "AUS"})
aus_portion.lineplot(hue="variable")

# %%
aus_portion.resample("AS")

# %%
production_emissions

# %%
# Assume that aus should be xx% of the global total. How much extra emissions do we need

assert config.emissions.high_production

target = config.emissions.high_production.target_share
assert 0.0 > target > 1.0  # noqa: PLR2004
target

# %%
target_aus_production_emissions = target * production_emissions
existing_aus_production_emissions = scmdata.ScmRun(
    production_emissions.timeseries() * aus_portion.resample("AS").values
)
extra_emissions = target_aus_production_emissions.subtract(
    existing_aus_production_emissions, op_cols={}
)
extra_emissions["variable"] = (
    extra_emissions["variable"] + "|" + extra_emissions["sector"]
)
extra_emissions["region"] = "AUS"
extra_emissions.timeseries()

# %%
scmdata.run_append(
    [
        production_emissions.set_meta("stage", "existing"),
        extra_emissions.set_meta("stage", "extra"),
    ]
).lineplot(hue="variable", style="stage")

# %%
extra_emissions.line_plot(hue="variable")

# %% [markdown]
# # Compare old + new aus

# %%
aus_emissions

# %%
extra_emissions.drop_meta(["carrier", "product", "method"]).set_meta("region", "AUS")

# %%
new_aus_emissions = aus_emissions.add(
    extra_emissions.drop_meta(["carrier", "product", "method", "sector"]), op_cols={}
)
new_aus_emissions["stage"] = "new"
new_aus_emissions

# %%


# %%
scmdata.run_append(
    [new_aus_emissions, aus_emissions.set_meta("stage", "old")]
).lineplot(hue="variable", style="stage", time_axis="year")
plt.gca().set_xlim(2015, 2100)
plt.gca().set_ylabel("kt/yr")

# %%
country_emissions.filter(region="AUS").process_over(["variable"], "sum")

# %%
extra_emissions.timeseries()

# %%
extra_emissions.to_csv(config.emissions.high_production.output_file)

# %%
