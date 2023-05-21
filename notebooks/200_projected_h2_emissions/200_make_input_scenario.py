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
# # Make input files
#
# This notebook creates the input scenario that is used to drive
# this pipeline.
#

# %%
from typing import Any

import scmdata

from local.config import TimeseriesOperation, load_config_from_file
from local.h2_adjust.constants import (
    HYDROGEN_PRODUCTS,
    R5_REGIONS,
    InputRequirement,
)

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
# Create a list of the required input variables

required_input_variables: list[InputRequirement] = [
    InputRequirement(
        filters={"variable": "Secondary Energy|Hydrogen"},
        checks=[("region", [*R5_REGIONS, "World"])],
    ),
]
# Check that we have sectoral baseline emissions to use for downscaling/gridding
for product in HYDROGEN_PRODUCTS:
    if product == "H2":
        continue
    if product == "N2O":
        required_input_variables.append(
            InputRequirement(
                filters={"variable": f"Baseline Emissions|{product}"},
                checks=[("region", ["World"])],
            )
        )
        continue
    required_input_variables.append(
        InputRequirement(
            filters={"variable": f"Baseline Emissions|{product}|Energy Sector"},
            checks=[("region", [*R5_REGIONS, "World"])],
        )
    )
    required_input_variables.append(
        InputRequirement(
            filters={"variable": f"Baseline Emissions|{product}|Transportation Sector"},
            checks=[("region", [*R5_REGIONS, "World"])],
        )
    )

    # There are no CH4 emissions from aircraft available
    if product != "CH4":
        required_input_variables.append(
            InputRequirement(
                filters={"variable": f"Baseline Emissions|{product}|Aircraft"},
                checks=[("region", ["World"])],
            )
        )
    required_input_variables.append(
        InputRequirement(
            filters={
                "variable": f"Baseline Emissions|{product}|International Shipping"
            },
            checks=[("region", ["World"])],
        )
    )


# %%
# Use IAM and CMIP6 database
# Fetched manually from https://tntcat.iiasa.ac.at/SspDb/dsd?Action=htmlpage&page=60


# %%
# Load data
def _run_operation(operation: TimeseriesOperation):
    run = scmdata.ScmRun(operation.input_file, lowercase_cols=True)
    run = run.filter(**operation.filters)

    for rename in operation.renames:
        run[rename.dimension] = run[rename.dimension].str.replace(
            rename.target, rename.to
        )

    return run


input_scenario = scmdata.run_append(
    [_run_operation(operation) for operation in config.emissions.cleaning_operations]
)

# Override metadata for the combined set of timeseries
# Overrides the entire metadata dimension
for key, value in config.emissions.metadata.items():
    input_scenario[key] = value

# %%
# Check that the scenario contains the required variables

for requirement in required_input_variables:
    checks = requirement.checks
    filtered_data = input_scenario.filter(**requirement.filters)

    missing_values: list[tuple[str, Any]] = []
    for metadata_dimension, required_values in checks:
        vals: list[Any] = filtered_data.get_unique_meta(metadata_dimension)

        for v in required_values:
            if v not in vals:
                missing_values.append((metadata_dimension, v))

    if missing_values:
        raise ValueError(f"Missing {missing_values} from {requirement.filters}")  # noqa

config.emissions.input_scenario.parent.mkdir(parents=True, exist_ok=True)
input_scenario.to_csv(config.emissions.input_scenario)
