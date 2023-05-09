"""
Serialisation
"""
from __future__ import annotations

from typing import Any

import cattrs.preconf.pyyaml

converter_yaml = cattrs.preconf.pyyaml.make_converter()
"""Yaml serializer"""


def parse_placeholders(in_str: str, **kwargs: Any) -> str:
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
