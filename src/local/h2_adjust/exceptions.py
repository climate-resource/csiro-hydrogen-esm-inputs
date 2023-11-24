"""
Exception classes
"""


class SanitizeError(ValueError):
    """
    Error when sanitizing a unit
    """

    def __init__(self, unit: str):
        super().__init__(f"Could not sanitize: {unit}")
