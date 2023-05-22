"""
Serialisation

This is currently specific to how we have set this project up. There are
probably general patterns we could go with, but this is so little code I'm not
sure it's worth making general pattern assumptions yet.
"""
from __future__ import annotations

from pathlib import Path

import cattrs.preconf.pyyaml

converter_yaml = cattrs.preconf.pyyaml.make_converter()
"""Yaml serializer"""

converter_yaml.register_unstructure_hook(Path, lambda p: str(p))
converter_yaml.register_structure_hook(Path, lambda p, _: Path(p))


def parse_placeholders(in_str: str, **kwargs: str | float | int) -> str:
    """
    Parse placeholders in a raw string

    Parameters
    ----------
    in_str
        Raw string

    **kwargs
        Replacements to be made

    Returns
    -------
        String, with all appearances of ``{kwarg}`` replaced by their value

    Examples
    --------
    >>> parse_placeholders("Hi I am {name}!", name="Tim")
    'Hi I am Tim'
    """
    return in_str.format(**kwargs)
