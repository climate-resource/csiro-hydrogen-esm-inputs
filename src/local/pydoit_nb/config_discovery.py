"""
Tools to help with config discovery
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

glob_config_files_task_params: list[dict[str, Any]] = [
    {
        "name": "configdir",
        "default": Path("data") / "raw" / "configuration",
        "type": Path,
        "long": "configdir",
        "help": "Path from which to load configuration",
    },
    {
        "name": "configglob",
        "default": "*.yaml",
        "type": str,
        "long": "configglob",
        "help": "Glob to use when looking for configuration files",
    },
]
"""
Task parameters to use when discovering files with glob
"""


def glob_config_files(configdir: Path, configglob: str) -> Iterable[Path]:
    """
    Glob config files within a directory

    Parameters
    ----------
    configdir
        Directory in which to look

    configglob
        Glob to apply

    Returns
    -------
        Found files that match the glob
    """
    return configdir.glob(configglob)