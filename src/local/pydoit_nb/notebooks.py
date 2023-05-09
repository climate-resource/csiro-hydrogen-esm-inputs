"""
Notebook running handling
"""
import logging
import os.path
from typing import Protocol

import jupytext
import papermill as pm
from attrs import define

LOGGER = logging.getLogger(__name__)


@define
class NotebookStep:
    """
    A step which runs a single notebook that has dependencies and targets
    """

    name: str
    """Name of the step"""

    notebook: str
    """
    Path to the notebook to run

    This notebook will be run with papermill and passed a single parameter,
    ``config_file``, which will be a path to the config file to use to run the
    notebook.
    """

    dependencies: list[str]  # TODO: tuples might be a better choice here as immutable?
    """
    Paths to the files on which the notebooks outputs depend
    """

    targets: list[str]
    """
    Paths this notebook creates
    """


class NotebookExecutionException(Exception):
    """
    Raised when a notebook fails to execute for any reason
    """
    def __init__(self, exc, filename):
        self.exc = exc
        self.filename = filename
        super().__init__(self.exc)

    def __str__(self):
        return f"{self.filename} failed to execute: {self.exc}"


# TODO: switch to paths
def run_notebook(
    base_notebook: str,
    output_notebook_dir: str,
    config_file: str,
    suffix_unexecuted: str = "-unexecuted",
    config_file_parameter_name: str = "config_file",
) -> None:
    """
    Run a notebook

    This loads the notebook ``base_notebook`` using jupytext, then writes it
    as a ``.ipynb`` file with suffix ``suffix_unexecuted`` into
    ``output_notebook_dir``. It then runs this notebook with papermill,
    writing it to a notebook file without the ``suffix_unexecuted``. The
    ``config_file`` is parsed to the notebook as a parameter with name
    ``"config_file"`` via papermill.

    Variation of `h2_adjust.adjust.run_notebook`

    Parameters
    ----------
    base_notebook
        Notebook from which to start

    output_notebook_dir
        Where to write the output notebooks

    config_file
        Config file to use when running the notebooks

    suffix_unexecuted
        Suffix to use when writing unexecuted notebooks

    config_file_parameter_name
        Parameter name to use when passing ``config_file`` to the notebook
        while running with papermill
    """
    LOGGER.info("Reading raw notebook with jupytext: %s", base_notebook)
    notebook_jupytext = jupytext.read(base_notebook)

    notebook = os.path.splitext(os.path.basename(base_notebook))[0]
    output_template_fname = os.path.join(
        output_notebook_dir, f"{notebook}{suffix_unexecuted}.ipynb"
    )

    LOGGER.info("Writing unexecuted notebook: %s", output_template_fname)
    jupytext.write(
        notebook_jupytext,
        output_template_fname,
        fmt="ipynb",
    )

    try:
        LOGGER.info("Executing notebook: %s", output_template_fname)
        pm.execute_notebook(
            output_template_fname,
            os.path.join(output_notebook_dir, f"{notebook}.ipynb"),
            parameters={config_file_parameter_name: config_file},
        )
    except Exception as exc:
        raise NotebookExecutionException(e, output_template_fname) from exc
