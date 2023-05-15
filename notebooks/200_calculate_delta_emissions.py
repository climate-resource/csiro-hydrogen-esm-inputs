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
# Calculate changes in emissions.

# %%
import os
import os.path

from local.config import load_config_from_file

# %% tags=["parameters"]
config_file: str = "dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)
config

# %%
with open(config.delta_emissions.input_file) as fh:
    loaded = fh.read()

loaded

# %%
os.makedirs(os.path.dirname(config.delta_emissions.output_file), exist_ok=True)
with open(config.delta_emissions.output_file, "w") as fh:
    fh.write(loaded)
    fh.write("Some more text.")
