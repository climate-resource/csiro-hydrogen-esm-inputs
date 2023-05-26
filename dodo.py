"""
doit configuration file
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

from doit import task_params

from local.config import (
    ConfigBundle,
    get_config_bundle,
    write_config_file_in_output_dir,
)
from local.key_info import get_key_info
from local.parameters import (
    config_files_task_params,
    config_task_params,
    notebook_step_task_params,
)
from local.pydoit_nb.config_discovery import (
    glob_config_files,
)
from local.steps import (
    gen_crunch_historical_tasks,
    gen_crunch_scenario_tasks,
    gen_finalise_tasks,
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

logFormatter = logging.Formatter(
    "%(levelname)s - %(asctime)s %(name)s %(processName)s (%(module)s:%(funcName)s:%(lineno)d):  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
stdoutHandler = logging.StreamHandler()
stdoutHandler.setFormatter(logFormatter)

root_logger.addHandler(stdoutHandler)

logger = logging.getLogger("dodo")


def print_key_info() -> None:
    """
    Print key information
    """
    key_info = get_key_info().split("\n")
    longest_line = max(len(line) for line in key_info)
    top_line = bottom_line = "=" * longest_line

    print("\n".join([top_line, *key_info, bottom_line]))

    time.sleep(1.5)


def task_display_info() -> dict[str, Any]:
    """
    Generate task which displays key information

    Returns
    -------
        pydoit task
    """
    return {
        "actions": [print_key_info],
    }


def print_config_bundle(cb: ConfigBundle) -> None:
    """
    Print configuration bundle info

    Parameters
    ----------
    cb
        Config bundle
    """
    print(
        f"Will run {cb.stub!r} with bundle serialised "
        f"in: {cb.config_hydrated_path!r}"
    )


def get_show_config_tasks(
    config_bundles: Iterable[ConfigBundle],
) -> Iterable[dict[str, Any]]:
    """
    Get tasks which show the configuration we're using

    Parameters
    ----------
    config_bundles
        Configuration bundles to show

    Returns
    -------
        pydoit tasks
    """
    base_task = {
        "name": None,
        "doc": "Show configurations to run",
    }
    yield {**base_task}

    for cb in config_bundles:
        yield {
            **base_task,
            "name": cb.stub,
            "actions": [(print_config_bundle, (), {"cb": cb})],
        }


@task_params(
    [
        *config_files_task_params,
        *config_task_params,
        *notebook_step_task_params,
    ]
)
def task_generate_notebook_tasks(  # noqa: PLR0913
    configdir,
    configglob_scenarios,
    output_root_dir,
    run_id,
    raw_notebooks_dir,
    common_configuration,
    user_placeholders,
) -> Iterable[dict[str, Any]]:
    """
    Generate tasks based on notebooks
    """
    # Discovery: find all the config files to use
    config_files = glob_config_files(configdir, configglob_scenarios)

    # Hydration: parse the config files and fill all the placeholders
    #   how to combine stub and raw names etc.
    config_bundles = [
        get_config_bundle(
            cf,
            output_root_dir=output_root_dir,
            run_id=run_id,
            common_config_file=common_configuration,
            user_placeholder_file=user_placeholders,
        )
        for cf in config_files
    ]

    if not config_bundles:
        logger.warning("No scenario configuration files found")
        # Early return if no files are found
        return

    # Serialise hydrated config back to disk
    # #3: If we ever want to optimise, but probably unnecessary
    [write_config_file_in_output_dir(cb) for cb in config_bundles]

    yield from get_show_config_tasks(config_bundles)

    yield from gen_crunch_historical_tasks(
        config_bundles,
        raw_notebooks_dir.absolute(),
    )

    yield from gen_crunch_scenario_tasks(
        config_bundles,
        raw_notebooks_dir.absolute(),
    )

    yield from gen_finalise_tasks(
        config_bundles,
        raw_notebooks_dir.absolute(),
    )
