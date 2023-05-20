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
# # Download CMIP6 data
#
# Here we download the original CMIP6 data.

# %%
import urllib

from local.config import load_config_from_file
from local.pydoit_nb.checklist import generate_directory_checklist

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
gridded_file_base = "http://aims3.llnl.gov/thredds/fileServer/user_pub_work/input4MIPs/CMIP6/ScenarioMIP/UoM/UoM-{scenario}-1-2-1/atmos/mon/{variable_under}/gn-15x360deg/v20181127/{variable}_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{scenario}-1-2-1_gn-15x360deg_201501-250012.nc"
gmnhsh_file_base = "http://aims3.llnl.gov/thredds/fileServer/user_pub_work/input4MIPs/CMIP6/ScenarioMIP/UoM/UoM-{scenario}-1-2-1/atmos/mon/{variable_under}/gr1-GMNHSH/v20181127/{variable}_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-{scenario}-1-2-1_gr1-GMNHSH_201501-250012.nc"


def format_base(b, s, v):
    """
    Format base url
    """
    return b.format(scenario=s, variable=v, variable_under=v.replace("-", "_"))


# %%
for s in config.cmip6_concentrations.concentration_scenario_ids:
    for v in config.cmip6_concentrations.concentration_variables:
        for to_download in [
            format_base(gridded_file_base, s=s, v=v),
            format_base(gmnhsh_file_base, s=s, v=v),
        ]:
            filename = (
                config.cmip6_concentrations.root_raw_data_dir
                / to_download.split("/")[-1]
            )
            filename.parent.mkdir(parents=True, exist_ok=True)
            if filename.exists():
                print(f"Already exists: {filename}")
            else:
                print(f"Downloading: {to_download}")
                filename_resp, resp = urllib.request.urlretrieve(  # noqa: S310
                    to_download, filename
                )
                print(f"Saving to: {filename}")

# %%
generate_directory_checklist(config.cmip6_concentrations.root_raw_data_dir)
