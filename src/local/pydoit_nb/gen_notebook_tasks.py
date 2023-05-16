"""
Utility wrappers around :mod:`pydoit`
"""
from __future__ import annotations

import os
from collections.abc import Hashable, Iterable, Iterator
from pathlib import Path
from typing import Any, Protocol

from doit.tools import config_changed  # type: ignore

from local.pydoit_nb.notebooks import run_notebook
from local.serialization import converter_yaml


class SupportsGenNotebookTasks(Protocol):
    """
    Class which supports generating notebook running tasks
    """

    name: str
    """Name of the task. This should be unique in the whole workflow"""

    raw_notebook: os.PathLike[str]
    """Path to raw notebook"""

    unexecuted_notebook: os.PathLike[str]
    """Path to unexecuted notebook"""

    executed_notebook: os.PathLike[str]
    """Path to executed notebook"""

    configuration: Hashable | None
    """
    Configuration used by the notebook.

    If any of the configuration changes then the notebook will be triggered.

    If nothing is provided, then the notebook will be run whenever the configuration
    file driving the notebook is modified.
    """

    dependencies: tuple[Path, ...]
    """Paths on which the notebook depends"""

    targets: tuple[Path, ...]
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

        if step.configuration is not None:
            task["uptodate"] = (
                config_changed(
                    converter_yaml.dumps(step.configuration, sort_keys=True),
                ),
            )
        else:
            # Trigger the notebook whenever the configuration file changes
            task["file_dep"] += (config_file,)  # type: ignore

        yield task
