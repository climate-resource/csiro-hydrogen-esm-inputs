"""
doit configuration file
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from doit import task_params

from local.config import (
    ConfigBundle,
    get_config_bundle,
    write_config_file_in_output_dir,
)
from local.parameters import (
    config_files_task_params,
    config_task_params,
    notebook_step_task_params,
)
from local.pydoit_nb.config_discovery import (
    glob_config_files,
)
from local.steps import gen_crunch_historical_tasks, gen_crunch_scenario_tasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dodo")


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
        # I think Jared might have had the idea to also make the tasks
        # uptodate depend on the value of the input params, but I don't think
        # it was implemented
    )

    yield from gen_crunch_scenario_tasks(
        config_bundles,
        raw_notebooks_dir.absolute(),
        # I think Jared might have had the idea to also make the tasks
        # uptodate depend on the value of the input params, but I don't think
        # it was implemented
    )
