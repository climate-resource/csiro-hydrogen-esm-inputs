"""
Tools to help with config discovery
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import yaml
from typing import Any
import deepmerge

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
        "default": "scenarios/*.yaml",
        "type": str,
        "long": "configglob",
        "help": "Glob to use when looking for configuration files",
    },
    {
        "name": "common_configuration",
        "default": "common.yaml",
        "type": str,
        "long": "common_configuration",
        "help": "Common configuration shared by all configurations",
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


def load_config_fragment(filename: Path) -> dict[str, Any]:
    """
    Load a configuration fragment

    This configuration fragment may be a subset of a complete :class:`Config`
    and may also include some placeholders that will be filled in later.

    Parameters
    ----------
    filename
        Filename containing the configuration fragment

        This file must be in YAML format

    Returns
    -------
        Fragment of a :class:`Config` object
    """
    with open(filename) as fh:
        resp = fh.read()

    return yaml.safe_load(resp)


def merge_config_fragments(
    base: dict[str, Any], *fragments: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge together multiple fragments

    A recursive deep merge is performed which merges together dicts so each
    fragment can have a different set of keys which are joined together to
    form a complete set. If any duplicate keys are present the later fragment
    takes precedece. In the case of overlapping values of `list` or `set` type,
    the later fragment will override the previous value.

    .. note:

        This modified the base fragment in place. If that is not desired
        perform a deepcopy of the fragment before passing.

    Parameters
    ----------
    base
        Base fragment

        Modified inplace during the merging

    fragments
        A collection of configuration fragments

        These fragments

    Returns
    -------
        A merged set of configuration fragments
    """
    # Aggressive merging strategy which always preferences the updated value
    # and replaces any matching lists/sets rather than the default behaviour
    # of merging
    merge_strategies = (
        (list, "override"),
        (dict, "merge"),
        (set, "override"),
    )
    merger = deepmerge.Merger(merge_strategies, ["override"], ["override"])

    res = base

    for fragment in fragments:
        res = merger.merge(res, fragment)

    return res
