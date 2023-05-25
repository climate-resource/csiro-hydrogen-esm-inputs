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
# # Compare MAGICC7 output with CMIP6 concentrations

# %%
import matplotlib.pyplot as plt  # type: ignore
import pooch  # type: ignore
import scmdata

from local.config import load_config_from_file

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
# TODO: Use bookshelf for this instead
rcmip_concs = pooch.retrieve(
    path=config.rcmip.concentrations_path.parent,
    url="https://rcmip-protocols-au.s3-ap-southeast-2.amazonaws.com/v5.1.0/rcmip-concentrations-annual-means-v5-1-0.csv",
    fname=config.rcmip.concentrations_path.name,
    known_hash="b6749ea32cc36eb0badc5d028b5b7b7bbcc56606144155fa2c0c3f9ceeac18c9",
    progressbar=True,
)

ssps = scmdata.ScmRun(str(rcmip_concs), lowercase_cols=True)
ssps

# %%
PROJECTIONS_FILE = config.magicc_runs.output_file
projections_magicc7 = scmdata.ScmRun.from_nc(str(PROJECTIONS_FILE))
projections_magicc7

# %%
for vdf in projections_magicc7.groupby("variable"):
    variable = vdf.get_unique_meta("variable", True)
    scenarios = vdf.get_unique_meta("scenario")
    scenarios_cmip6 = list(set([s.split("-")[0] for s in scenarios]))

    cmip6_vdf = ssps.filter(scenario=scenarios_cmip6, region="World", variable=variable)

    pdf = vdf.append(cmip6_vdf)
    pdf.filter(year=range(1950, 2100 + 1)).lineplot(style="variable")

    plt.show()
