"""
Pydoit related code
"""
from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING, Any

from local.config import Config, load_config
from local.notebooks import run_notebook
from local.serialization import converter_yaml, parse_placeholders

if TYPE_CHECKING:
    # move to local.steps?
    from local.notebooks import NotebookStep


def get_stub(file_name: str) -> str:
    """
    Get stub for a set of tasks

    Parameters
    ----------
    file_name
        Name of the config file

    Returns
    -------
        Stub
    """
    return os.path.splitext(file_name)[0]


def write_config_file_in_output_dir(
    config_file_in: str,
    config_file_out: str,
    output_root_dir: str,
    run_id: str,
    stub: str,
    **kwargs: Any,
) -> Config:
    """
    Write config file in output directory

    This parses all the placeholders in the config file before writing to the
    output directory

    Parameters
    ----------
    config_file_in
        Input configuration file

    config_file_out
        Where to write the updated config file

    output_root_dir
        Where to write the output files

    run_id
        ID for the run

    stub
        Stub for this particular set of config (effectively just a short name)

    **kwargs
        Passed to :func:`parse_placeholders`

    Returns
    -------
        Parsed config
    """
    with open(config_file_in, "r") as fh:
        loaded_str = fh.read()

    loaded_str_parsed = parse_placeholders(
        loaded_str,
        output_root_dir=output_root_dir,
        run_id=run_id,
        stub=stub,
        **kwargs,
    )

    config_parsed = load_config(loaded_str_parsed)

    os.makedirs(os.path.dirname(config_file_out), exist_ok=True)
    with open(config_file_out, "w") as fh:
        fh.write(converter_yaml.dumps(config_parsed))

    return config_parsed


# TODO: clean up (docstring, type hints etc.)
def gen_run_notebook_tasks(
    notebook_steps: list[NotebookStep],
    raw_notebooks_dir: str,
    output_notebook_dir: str,
    config_file: str,
    stub: str,
) -> Generator[dict[str, Any]]:
    """
    Generate notebook running tasks

    Parameters
    ----------
    notebook_steps
        Notebook steps to be run

    raw_notebooks_dir
        Directory in which the raw notebooks can be found

    output_notebook_dir
        Where to save the notebooks when they're run

    config_file
        Configuration file to use when running the notebooks

    stub
        Stub for this task (derived from the config file generally)

    Yields
    ------
        Tasks to run with pydoit
    """
    os.makedirs(output_notebook_dir, exist_ok=True)
    for step in notebook_steps:
        # This assumes that all notebooks are in the same directory (or
        # unobvious hacks are needed to get around this code structure)
        raw_notebook_path = os.path.join(raw_notebooks_dir, f"{step.notebook}.py")

        dependencies = (
            *step.dependencies,
            raw_notebook_path,  # Make sure the task also re-runs if the raw notebook changes
            config_file,  # Make sure the task also re-runs if the config changes
        )

        task = {
            "name": f"{stub}_{step.name}",
            "actions": [
                (
                    run_notebook,
                    [],
                    {
                        "base_notebook": raw_notebook_path,
                        "output_notebook_dir": output_notebook_dir,
                        "config_file": config_file,
                    },
                )
            ],
            "targets": step.targets,
            "file_dep": dependencies,
            "clean": True,  # if we run doit clean, remove the targets
        }

        yield task
