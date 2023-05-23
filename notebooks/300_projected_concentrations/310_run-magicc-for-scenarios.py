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
# # Run MAGICC
#
# Run MAGICC for the scenarios, now updated based on assumptions around emissions from a hydrogen economy.

# %%
import datetime as dt
import json
import os.path

import openscm_runner
import pymagicc.definitions
import scmdata

from local.config import load_config_from_file

# %% tags=["parameters"]
config_file: str = "../dev.yaml"  # config file

# %%
config = load_config_from_file(config_file)

# %%
config.magicc_runs

# %%
# How many configurations to run
N_CFGS_TO_RUN = config.magicc_runs.n_cfgs_to_run
N_CFGS_TO_RUN

# %%
OUTPUT_FILE = config.magicc_runs.output_file
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE

# %% [markdown]
# ## Run configs

# %% [markdown]
# These are hard-coded on purpose.

# %%
common_cfgs = {
    "startyear": 1750,
    "endyear": 2105,
    # use MAGICC names here, they are translated
    # to more readable names below
    "out_dynamic_vars": [
        "DAT_SURFACE_TEMP",
        "DAT_CO2_CONC",
        "DAT_CH4_CONC",
        "DAT_N2O_CONC",
        "DAT_HEAT_EARTH",
        "DAT_HEATCONTENT_AGGREG_TOTAL",
    ],
    "out_ascii_binary": "BINARY",
    "out_binary_format": 2,
    # Switch from conc to emissions driven in 2015
    "co2_switchfromconc2emis_year": 2015,
    "ch4_switchfromconc2emis_year": 2015,
    "n2o_switchfromconc2emis_year": 2015,
    "fgas_switchfromconc2emis_year": 2015,
    "mhalo_switchfromconc2emis_year": 2015,
}
common_cfgs

# %%
with open(config.magicc_runs.ar6_probabilistic_distribution_file) as fh:
    cfgs_base = json.load(fh)

# %%
run_cfgs = [
    {
        **common_cfgs,
        **c["nml_allcfgs"],
    }
    for c in cfgs_base["configurations"][:N_CFGS_TO_RUN]
]


# %% [markdown]
# ## Input emissions

# %%
scenarios = scmdata.ScmRun(config.emissions.magicc_scenario).filter(
    variable=["Emissions|H2"], keep=False
)
scenarios


# %% [markdown]
# Extend 5 years to avoid annoying jump at end of run.


# %%
def to_openscm(inrun: scmdata.ScmRun) -> scmdata.ScmRun:
    """
    Convert to OpenSCM-Runner conventions
    """

    def rename_variable(invar: str) -> str:
        """
        Rename variable to OpenSCM-Runner conventions
        """
        return (
            invar.replace("NMVOC", "VOC")
            .replace("SOx", "Sulfur")
            .replace("HFC245ca", "HFC245fa")
            .replace("|AFOLU", "|MAGICC AFOLU")
            .replace(
                "|Energy and Industrial Processes",
                "|MAGICC Fossil and Industrial",
            )
            .replace("F-Gases|", "")
            .replace("HFC|", "")
            .replace("Montreal Gases|", "")
            .replace("PFC|", "")
            .replace("CFC|", "")
        )

    out = inrun.copy()
    out["variable"] = out["variable"].apply(rename_variable)
    out["unit"] = out["unit"].apply(rename_variable)

    return out


# %%
scenarios = scenarios.interpolate(
    [
        dt.datetime(y, 1, 1)
        for y in range(scenarios["year"].min(), common_cfgs["endyear"] + 1)
    ],
    extrapolation_type="constant",
)
scenarios = to_openscm(scenarios)
scenarios.filter(variable="Emissions|BC").lineplot()
scenarios


# %%
def get_openscm_runner_output_names(magicc_names: list[str]) -> list[str]:
    """
    Get OpenSCM-Runner output names
    """
    return [
        pymagicc.definitions.convert_magicc7_to_openscm_variables(
            magiccvarname
        ).replace("DAT_", "")
        for magiccvarname in magicc_names
    ]


# %%
openscm_runner_output_names = get_openscm_runner_output_names(
    magicc_names=common_cfgs["out_dynamic_vars"]
)
openscm_runner_output_names


# %%
# Feels like all of the environment variable stuff should be in a .env file
# because it is actually platform dependent
os.environ["MAGICC_EXECUTABLE_7"] = str(config.magicc_runs.magicc_executable_path)
os.environ["MAGICC_WORKER_ROOT_DIR"] = os.path.expanduser(
    str(config.magicc_runs.magicc_worker_root_dir)
)
os.environ["MAGICC_WORKER_NUMBER"] = str(config.magicc_runs.magicc_worker_number)
# not everyone will need this
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/opt/gfortran/lib/gcc/current/"

res = openscm_runner.run(
    {"MAGICC7": run_cfgs},
    scenarios,
    output_variables=openscm_runner_output_names,
)

# %%
res_median = res.filter(
    region="World", variable="Atmospheric Concentrations*"
).process_over("run_id", "median", as_run=True)
res_median.metadata = {}
res_median

# %%
res_median.to_nc(OUTPUT_FILE)
OUTPUT_FILE
