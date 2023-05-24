"""
Serialisation

This is currently specific to how we have set this project up. There are
probably general patterns we could go with, but this is so little code I'm not
sure it's worth making general pattern assumptions yet.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar, get_origin

import cattrs.preconf.pyyaml

converter_yaml = cattrs.preconf.pyyaml.make_converter()
"""Yaml serializer"""

converter_yaml.register_unstructure_hook(Path, lambda p: str(p))
converter_yaml.register_structure_hook(Path, lambda p, _: Path(p))

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


# TODO: This should be part of local.pydoit_nb
class FrozenDict(dict[KeyT, ValueT]):
    """
    A frozen version of a dict

    Values cannot be modified after creation
    """

    def __setitem__(self, key: KeyT, value: ValueT) -> None:
        """
        Raise an exception for
        """
        raise NotImplementedError

    def __hash__(self) -> int:  # type: ignore
        """
        Calculate the hash of the contents
        """
        return hash(tuple(sorted(self.items())))


converter_yaml.register_unstructure_hook_func(
    lambda cls: get_origin(cls) == FrozenDict, lambda p: dict(**p)
)
converter_yaml.register_structure_hook_func(
    lambda cls: get_origin(cls) == FrozenDict, lambda p, _: FrozenDict(**p)
)


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
