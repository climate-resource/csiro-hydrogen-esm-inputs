"""
Utility wrappers around :mod:`pydoit`
"""
import os
from collections.abc import Iterable, Iterator
from typing import Any, Protocol

from local.pydoit_nb.notebooks import run_notebook


class SupportsGenNotebookTasks(Protocol):
    """
    Class which supports generating notebook running tasks
    """

    name: str
    """Name of the task. This should be unique in the whole workflow"""

    raw_notebook: os.PathLike
    """Path to raw notebook"""

    unexecuted_notebook: os.PathLike
    """Path to unexecuted notebook"""

    executed_notebook: os.PathLike
    """Path to executed notebook"""

    dependencies: tuple[os.PathLike, ...]
    """Paths on which the notebook depends"""

    targets: tuple[os.PathLike, ...]
    """Paths which the notebook creates/controls"""


def gen_run_notebook_tasks(
    notebook_steps: Iterable[SupportsGenNotebookTasks],
    config_file: os.PathLike,
    clean: bool = True,
) -> Iterator[dict[str, Any]]:
    """
    Generate notebook running tasks

    Parameters
    ----------
    notebook_steps
        Notebook steps to be run

    config_file
        Configuration file to use when running the notebooks

    clean
        If we run doit clean, should we also remove the targets?

    Yields
    ------
        Tasks to run with pydoit
    """
    for step in notebook_steps:
        dependencies = (
            *step.dependencies,
            step.raw_notebook,  # Make sure the task also re-runs if the raw notebook changes
            config_file,  # Make sure the task also re-runs if the config changes
        )

        task = {
            "name": step.name,
            "actions": [
                (
                    run_notebook,
                    [],
                    {
                        "base_notebook": step.raw_notebook,
                        "unexecuted_notebook": step.unexecuted_notebook,
                        "executed_notebook": step.executed_notebook,
                        "config_file": config_file,
                    },
                )
            ],
            "targets": step.targets,
            "file_dep": dependencies,
            "clean": clean,
        }

        yield task
