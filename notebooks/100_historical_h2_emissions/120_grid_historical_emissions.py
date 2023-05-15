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
# # Grid emissions
#
# Take the sectoral delta emissions and downscale the R5 regional information to countries
#
# Aviation and International shipping are handled different from the other sectors.
# This is because CEDS only reports global totals for these sectors. These global
# totals are then used with a constant 2d pattern for shipping and a 3d pattern for aviation.

# %%
import logging

import scmdata
from aneris.gridding import Gridder  # type: ignore

import local.h2_adjust.units  # noqa
from local.config import load_config_from_file

logger = logging.getLogger("grid_historical_emissions")
logging.basicConfig(level=logging.INFO)

# %% tags=["parameters"]
config_file: str = "notebooks/dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)


# %%
output_dir = config.historical_h2_gridding.output_directory
output_dir.mkdir(parents=True, exist_ok=True)


# %% [markdown]
# # Grid Historical

# %%
historical_emissions = scmdata.ScmRun(
    str(config.historical_h2_emissions.baseline_h2_emissions_countries)
)

if config.historical_h2_gridding.fast:
    logger.warning(
        "Fast mode enabled. Only processing a subset of years. DO NOT USE IN PRODUCTION"
    )
    historical_emissions = historical_emissions.filter(
        year=list(range(1850, 2000, 25)) + list(range(2000, 2015, 5))
    )
historical_emissions.get_unique_meta("sector")

# %%
gridder = Gridder(
    grid_dir=str(config.historical_h2_gridding.grid_data_directory),
    proxy_definition_file=str(config.historical_h2_gridding.proxy_mapping),
    seasonality_mapping_file=str(config.historical_h2_gridding.seasonality_mapping),
    sector_type=config.historical_h2_gridding.sector_type,
)

gridded_emissions = gridder.grid(
    str(output_dir),
    historical_emissions.filter(sector="Aircraft", keep=False),
    chunk_years=50,
)
gridded_emissions

# %%
# Grid aircraft separately to keep memory requirements lower
gridded_emissions = gridder.grid(
    str(output_dir),
    historical_emissions.filter(sector="Aircraft"),
    chunk_years=50,
)

# %%
