"""
doit configuration file
"""
import datetime
import glob
import logging
import os
import os.path
from typing import Any, Iterable

from doit import task_params

from local.pydoit_nb.config_discovery import (
    glob_config_files,
    glob_config_files_task_params,
)
from local.config import (
    config_task_params,
    gen_crunch_scenario_tasks,
    get_config_bundle,
    notebook_step_task_params,
    write_config_file_in_output_dir,
)
from local.key_info import get_key_info


logging.basicConfig(level=logging.INFO)


def display_key_info() -> None:
    """
    Display the project's key information
    """
    print("----")
    print(get_key_info())
    print("----")


def task_display_info() -> dict[str, Any]:
    """
    Task to display key information
    """
    return {
        "actions": [display_key_info],
        "verbosity": 2,
        "uptodate": [False],
    }


@task_params(
    [
        *glob_config_files_task_params,
        *config_task_params,
        *notebook_step_task_params,
    ]
)
def task_crunch_scenarios(
    configdir, configglob, output_root_dir, run_id, raw_notebooks_dir
) -> Iterable[dict[str, Any]]:
    """
    Crunch a scenario's files
    """
    # Discovery: find all the config files to use
    config_files = glob_config_files(configdir, configglob)

    # Hydration: parse the config files and fill all the placeholders
    # - also implements logic related to where to write things in and out,
    #   how to combine stub and raw names etc.
    config_bundles = [
        get_config_bundle(cf, output_root_dir=output_root_dir, run_id=run_id)
        for cf in config_files
    ]

    # Serialise hydrated config back to disk
    # #3: If we ever want to optimise, but probably unnecessary
    [write_config_file_in_output_dir(cb) for cb in config_bundles]

    # Generate tasks based on notebooks: tell pydoit what to run
    # - gen_crunch_scenario_tasks and therein get_notebook_steps implements
    #   the logic related to putting notebooks in the right place, handling
    #   splitting of executed and unexecuted notebooks etc.
    for config_bundle in config_bundles:
        yield gen_crunch_scenario_tasks(config_bundle, raw_notebooks_dir.absolute())
