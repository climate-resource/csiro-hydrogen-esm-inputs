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
import shutil
import time

from local.config import load_config_from_file
from local.pydoit_nb.checklist import generate_directory_checklist

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
shutil.copyfile(
    config.gridding_preparation.raw_rscript, config.gridding_preparation.output_rscript
)
time.sleep(1)

# %%
generate_directory_checklist(config.gridding_preparation.zenoda_data_archive)
