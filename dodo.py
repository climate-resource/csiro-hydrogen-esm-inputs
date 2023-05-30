"""
doit configuration file
"""
from __future__ import annotations

import functools
import json
import logging
import shutil
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, TypeVar

from doit import task_params

import local
from local.config import (
    ConfigBundle,
    get_config_bundle,
    get_run_root_dir,
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

    finalise_tasks = list(
        gen_finalise_tasks(
            config_bundles,
            raw_notebooks_dir.absolute(),
        )
    )

    ft_targets = []
    for ft in finalise_tasks:
        yield ft
        if "targets" in ft:
            ft_targets.extend(ft["targets"])

    run_root_dir = get_run_root_dir(output_root_dir, run_id)
    repo_root_dir = Path(__file__).parent
    yield from gen_copy_source_tasks(
        repo_root_dir=repo_root_dir,
        run_root_dir=run_root_dir,
        file_dependencies=ft_targets,  # Force copying to happen last
        run_id=run_id,
    )


def gen_copy_source_tasks(
    repo_root_dir: Path,
    run_root_dir: Path,
    file_dependencies: Iterable[Path],
    run_id: str,
) -> Iterable[dict[str, Any]]:
    """
    Generate task which copies the source and other files to the output bundle

    Parameters
    ----------
    repo_root_dir
        Repository root directory

    run_root_dir
        The run's root directory

    file_dependencies
        The file dependencies for this task (usually the output of the last
        set of runs so that this step happens only if everything else
        succeeded)

    run_id
        ID of this run

    Returns
    -------
        pydoit tasks
    """
    readme_name = "README.md"
    zenodo_name = "zenodo.json"
    other_files_to_copy = [
        "dodo.py",
        "poetry.lock",
        "pyproject.toml",
    ]
    src_dir = "src"

    yield {
        "basename": "copy source into bundle",
        "actions": [
            (
                copy_readme,
                [repo_root_dir / readme_name, run_root_dir / readme_name, run_id],
                {},
            ),
            (
                copy_zenodo,
                [
                    repo_root_dir / zenodo_name,
                    run_root_dir / zenodo_name,
                    local.__version__,
                ],
                {},
            ),
            *(
                (
                    swallow_output(shutil.copy2),
                    [repo_root_dir / file, run_root_dir / file],
                    {},
                )
                for file in other_files_to_copy
            ),
            (
                swallow_output(shutil.copytree),
                [repo_root_dir / src_dir, run_root_dir / src_dir],
                dict(
                    ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
                    dirs_exist_ok=True,
                ),
            ),
        ],
        "file_dep": file_dependencies,
    }


T = TypeVar("T")


def swallow_output(func: Callable[[...], T]) -> Callable[[...], T]:
    """
    Decorate function so the output is swallowed

    This is needed to make pydoit recognise the task has run correctly

    Parameters
    ----------
    func
        Function to decorate

    Returns
    -------
        Decorated function
    """

    @functools.wraps(func)
    def out(*args: Any, **kwargs: Any) -> T:
        func(*args, **kwargs)

    return out


def copy_readme(in_path: Path, out_path: Path, run_id: str) -> None:
    """
    Copy README to the output bundle

    This also adds a note with pydoit information to the README in the bundle

    Parameters
    ----------
    in_path
        Path to raw README

    out_path
        Path to output README in the bundle

    run_id
        Run ID of this run
    """
    with open(in_path) as fh:
        raw = fh.read()

    footer = f"""
## Pydoit info

This README was created from the raw file as part of the {run_id!r} run with
[pydoit](https://pydoit.org/contents.html). The bundle should contain
everything required to reproduce the outputs. The environment can be
made with [poetry](https://python-poetry.org/)
in the standard way. Please disregard messages about the `Makefile` here."""
    with open(out_path, "w") as fh:
        fh.write(raw)
        fh.write(footer)


def copy_zenodo(in_path: Path, out_path: Path, version: str) -> None:
    """
    Copy Zenodo JSON file to the output bundle

    This updates the version information too

    Parameters
    ----------
    in_path
        Path to raw Zenodo file

    out_path
        Path to output Zenodo file in the bundle

    version
        Version to write in the Zenodo file
    """
    with open(in_path) as fh:
        zenodo_metadata = json.load(fh)

    zenodo_metadata["metadata"]["version"] = version

    with open(out_path, "w") as fh:
        fh.write(json.dumps(zenodo_metadata, indent=2))
