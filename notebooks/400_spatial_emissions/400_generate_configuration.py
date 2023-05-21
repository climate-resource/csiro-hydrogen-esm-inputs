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
# # Generate config
#
# From the scenario config generate the DownscalingConfig object to be used

# %%
import logging
from pathlib import Path

from spaemis.config import DownscalingScenarioConfig, converter

from local.config import (
    ConfigSpatialEmissions,
    ConfigSpatialEmissionsScalerTemplate,
    load_config_from_file,
)
from local.serialization import parse_placeholders

logger = logging.getLogger("200_run_projection")
logging.basicConfig(level=logging.INFO)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file
name: str = "ssp119_australia"

# %%
config = load_config_from_file(config_file)


# %%
def find_config_match(iterable: list[ConfigSpatialEmissions]):
    """Get the first spatial emissions config with a matching name"""
    return next(run_config for run_config in iterable if run_config.name == name)


spaemis_config = find_config_match(config.spatial_emissions)
spaemis_config


# %%
def prepare_scaler_template(
    template_file: ConfigSpatialEmissionsScalerTemplate, **kwargs
) -> Path:
    """
    Load and insert placeholders from a template file
    """
    with open(template_file.input_file) as fh:
        contents = parse_placeholders(fh.read(), **kwargs)
    template_file.output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(template_file.output_file, "w") as fh:
        fh.write(contents)

    return template_file.output_file


scalers = [
    prepare_scaler_template(template, **spaemis_config.scalar_template_replacements)
    for template in spaemis_config.scaler_templates
]
templated_config = {**spaemis_config.configuration_template}

if "source_files" in templated_config["scalers"]:
    templated_config["scalers"]["source_files"].extend(scalers)
else:
    templated_config["scalers"]["source_files"] = scalers

downscaling_config = converter.structure(templated_config, DownscalingScenarioConfig)

# %%
spaemis_config.downscaling_config.parent.mkdir(parents=True, exist_ok=True)
with open(spaemis_config.downscaling_config, "w") as fh:
    fh.write(converter.dumps(downscaling_config, DownscalingScenarioConfig))
