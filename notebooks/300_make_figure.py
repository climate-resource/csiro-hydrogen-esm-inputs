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
import os
import os.path

from local.config import load_config_from_file

# %% tags=["parameters"]
config_file: str = "dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)
config

# %%
with open(config.delta_emissions.output_file) as fh:
    loaded = fh.read()

loaded

# %%
os.makedirs(os.path.dirname(config.output_final_figure), exist_ok=True)
with open(config.output_final_figure, "w") as fh:
    fh.write("A nice figure")
