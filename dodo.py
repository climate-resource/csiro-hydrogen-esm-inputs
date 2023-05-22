"""
doit configuration file
"""
import logging
from collections.abc import Iterable
from typing import Any

from doit import task_params

from local.config import (
    ConfigBundle,
    config_task_params,
    gen_crunch_scenario_tasks,
    get_config_bundle,
    notebook_step_task_params,
    write_config_file_in_output_dir,
)
from local.key_info import get_key_info
from local.pydoit_nb.config_discovery import (
    glob_config_files,
    glob_config_files_task_params,
)

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
        *glob_config_files_task_params,
        *config_task_params,
        *notebook_step_task_params,
    ]
)
def task_generate_notebook_tasks(  # noqa: PLR0913
    configdir,
    configglob,
    output_root_dir,
    run_id,
    raw_notebooks_dir,
    common_configuration,
) -> Iterable[dict[str, Any]]:
    """
    Generate notebook tasks
    """
    # Discovery: find all the config files to use
    config_files = glob_config_files(configdir, configglob)

    # Hydration: parse the config files and fill all the placeholders
    # - also implements logic related to where to write things in and out,
    #   how to combine stub and raw names etc.
    config_bundles = [
        get_config_bundle(
            cf,
            output_root_dir=output_root_dir,
            run_id=run_id,
            common_config_file=configdir / common_configuration,
        )
        for cf in config_files
    ]

    # Serialise hydrated config back to disk
    # #3: If we ever want to optimise, but probably unnecessary
    [write_config_file_in_output_dir(cb) for cb in config_bundles]

    yield from get_show_config_tasks(config_bundles)

    # This might be able to be split if we used calc_dep or create_after
    # cleverly (might work with create_after as we can pre-calculate creates
    # based on the notebook names (which are passed to pydoit as basenames,
    # leaving name to hold onto the stubs), although I don't know whether that
    # will actually work because I don't really understand the name handling)

    # Generate tasks based on notebooks: tell pydoit what to run
    # - gen_crunch_scenario_tasks and therein get_notebook_steps implements
    #   the logic related to putting notebooks in the right place, handling
    #   splitting of executed and unexecuted notebooks etc.
    for config_bundle in config_bundles:
        yield from gen_crunch_scenario_tasks(
            config_bundle,
            raw_notebooks_dir.absolute(),
            [*glob_config_files_task_params, *config_task_params],
        )
