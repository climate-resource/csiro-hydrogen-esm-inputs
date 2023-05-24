"""
Notebook running handling
"""
from __future__ import annotations

import logging
import os.path
from collections.abc import Hashable
from pathlib import Path

import jupytext
import papermill as pm
from attrs import define, frozen

from local.serialization import FrozenDict

LOGGER = logging.getLogger(__name__)


@frozen
class NotebookStep:
    """
    A step which runs a single notebook that has dependencies and targets
    """

    name: str
    """Name of the task"""

    stub: str
    """Stub. The combination of name and stub should be unique in the whole workflow"""

    doc: str
    """Longer description of the step"""

    raw_notebook: os.PathLike[str]
    """Path to raw notebook"""

    unexecuted_notebook: os.PathLike[str]
    """Path to unexecuted notebook"""

    executed_notebook: os.PathLike[str]
    """Path to executed notebook"""

    dependencies: tuple[Path, ...]
    """Paths on which the notebook depends"""

    targets: tuple[Path, ...]
    """Paths which the notebook creates/controls"""

    configuration: Hashable | None
    """
    Configuration used by the notebook.

    If any of the configuration changes then the notebook will be triggered.

    If nothing is provided, then the notebook will be run whenever the configuration
    file driving the notebook is modified.
    """
    # It looks like this solves a problem that even the original authors
    # hadn't thought about because they just suggest using forget here
    # https://pydoit.org/cmd-other.html#forget (although they also talk about
    # non-file dependencies elsewhere so maybe these are just out of date docs)

    notebook_parameters: FrozenDict[str, str]
    """Additional parameter values to pass to the notebook"""


@define
class SingleNotebookDirStep:
    """
    A step which runs a single notebook that has dependencies and targets

    This step also assumes that all notebooks are in the same root directory,
    which is configured from elsewhere
    """

    name: str
    """Name of the step"""

    doc: str
    """Longer description of the step"""

    notebook: str
    """
    Name of the notebook to run

    This notebook will be run with papermill and passed a single parameter,
    ``config_file``, which will be a path to the config file to use to run the
    notebook.

    Currently control over where this notebook is (i.e. which directory it is
    in) is assumed to be handled elsewhere. It may be desirable to break this
    assumption in future, but we haven't thought that through yet, PRs welcome.
    """

    raw_notebook_ext: str
    """
    Extension of the raw notebook

    Typically we use jupytext and papermill so this will be `.py` or `.md`
    """

    dependencies: tuple[Path, ...]
    """
    Paths to the files on which the notebooks outputs depend
    """

    targets: tuple[Path, ...]
    """
    Paths this notebook creates
    """

    configuration: Hashable | None = None
    """
    Configuration used by the notebook.
    """

    notebook_suffix: str = ""
    """Suffix to add to the resulting notebooks"""

    notebook_parameters: dict[str, str] | None = None
    """Additional parameter values to pass to the notebook"""

    def to_notebook_step(
        self,
        stub: str,
        raw_notebooks_dir: Path,
        output_notebook_dir: Path,
        unexecuted_suffix: str = "-unexecuted",
    ) -> NotebookStep:
        """
        Create :obj:`NotebookStep` from self

        This assumes that all the raw notebooks are in the same directory and
        that we want to write all output notebooks (executed and unexecuted)
        in the same directory

        Parameters
        ----------
        stub
            Stub to identify this step, separate from all others which may run
            the same notebooks but based on a different config

        raw_notebooks_dir
            Directory in which raw notebooks are stored

        output_notebook_dir
            Directory in which output notebooks should be written

        unexecuted_suffix
            Suffix to add to notebook names to indicate that they are
            unexecuted

        Returns
        -------
            Initialised instance
        """
        raw_notebook = raw_notebooks_dir / f"{self.notebook}{self.raw_notebook_ext}"

        unexecuted_notebook = (
            output_notebook_dir
            / f"{self.notebook}{self.notebook_suffix}{unexecuted_suffix}.ipynb"
        )
        executed_notebook = (
            output_notebook_dir / f"{self.notebook}{self.notebook_suffix}.ipynb"
        )
        notebook_parameters = FrozenDict(self.notebook_parameters or {})

        return NotebookStep(
            name=self.name,
            stub=stub,
            doc=self.doc,
            raw_notebook=raw_notebook,
            unexecuted_notebook=unexecuted_notebook,
            executed_notebook=executed_notebook,
            dependencies=self.dependencies,
            targets=self.targets,
            configuration=self.configuration,
            notebook_parameters=notebook_parameters,
        )


class NotebookExecutionException(Exception):
    """
    Raised when a notebook fails to execute for any reason
    """

    def __init__(self, exc, filename):
        self.exc = exc
        self.filename = filename
        super().__init__(self.exc)

    def __str__(self):
        """
        Get string representation of self
        """
        return f"{self.filename} failed to execute: {self.exc}"


def run_notebook(
    base_notebook: os.PathLike,
    unexecuted_notebook: Path,
    executed_notebook: Path,
    notebook_parameters: dict[str, str] | None = None,
) -> None:
    """
    Run a notebook

    This loads the notebook ``base_notebook`` using jupytext, then writes it
    as an ``.ipynb`` file to ``unexecuted_notebook``. It then runs this
    unexecuted notebook with papermill, writing it to ``executed_notebook``.

    Parameters
    ----------
    base_notebook
        Notebook from which to start

    unexecuted_notebook
        Where to write the unexecuted notebook

    executed_notebook
        Where to write the executed notebook

    notebook_parameters
        Parameters to pass to the target notebook

        These parameters will replace the contents of a cell tagged "parameters".
        See the
        `papermill documentation <https://papermill.readthedocs.io/en/latest/usage-parameterize.html#designate-parameters-for-a-cell>`_
        for more information about parameterizing a notebook.

    """
    LOGGER.info("Reading raw notebook with jupytext: %s", base_notebook)
    notebook_jupytext = jupytext.read(base_notebook)

    if notebook_parameters is None:
        notebook_parameters = {}

    LOGGER.info("Writing unexecuted notebook: %s", unexecuted_notebook)
    unexecuted_notebook.parent.mkdir(parents=True, exist_ok=True)
    jupytext.write(
        notebook_jupytext,
        unexecuted_notebook,
        fmt="ipynb",
    )

    try:
        LOGGER.info("Executing notebook: %s", unexecuted_notebook)
        executed_notebook.parent.mkdir(parents=True, exist_ok=True)
        pm.execute_notebook(
            unexecuted_notebook,
            executed_notebook,
            parameters=notebook_parameters,
        )
    except Exception as exc:
        raise NotebookExecutionException(exc, unexecuted_notebook) from exc
