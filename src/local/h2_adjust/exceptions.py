"""
Exception classes
"""


class SanitizeError(ValueError):
    """
    Error when sanitizing a unit
    """

    def __init__(self, source_unit: str, target_unit: str):
        super().__init__(f"Could not sanitize: {source_unit} -> {target_unit}")
