"""
Configuration class

Key definition of data
"""
from __future__ import annotations

from attrs import define

from local.notebooks import NotebookStep
from local.serialization import converter_yaml


@define
class ConfigDeltaEmissions:
    input_file: str
    """Input file"""

    output_file: str
    """Output file"""


@define
class ConfigAnthroBaseline:
    input_file: str
    """Input file"""


@define
class Config:
    output_root_dir: str
    """Root output directory"""

    output_notebook_dir: str
    """Notebook output directory"""

    delta_emissions: ConfigDeltaEmissions
    """Configuration for calculating the change in emissions"""

    anthro_baseline: ConfigAnthroBaseline
    """Configuration for calculating the change in anthropogenic baseline"""

    output_final_figure: str
    """Output file for final figure"""


def load_config_from_file(config_file: str) -> Config:
    """
    Load config from disk

    Parameters
    ----------
    config_file
        Configuration file

    Returns
    -------
        Loaded configuration
    """
    with open(config_file, "r") as fh:
        config = load_config(fh.read())

    return config


def load_config(config: str) -> Config:
    """
    Load config from a string

    Parameters
    ----------
    config
        Configuration string

    Returns
    -------
        Loaded configuration
    """
    return converter_yaml.loads(config, Config)


def get_notebook_steps(config: Config) -> list[NotebookStep]:
    """
    Get notebook steps

    This essentially defines the configuration of our entire workflow

    Parameters
    ----------
    config
        Configuration from which targets and dependencies can be inferred

    Returns
    -------
        Notebook steps to run
    """
    return [
        NotebookStep(
            name="make input files",
            notebook="000_make_input_files",
            dependencies=[],
            targets=[
                config.delta_emissions.input_file,
                config.anthro_baseline.input_file,
            ],
        ),
        NotebookStep(
            name="calculate delta emissions",
            notebook="200_calculate_delta_emissions",
            dependencies=[config.delta_emissions.input_file],
            targets=[
                config.delta_emissions.output_file,
            ],
        ),
        NotebookStep(
            name="create final figure",
            notebook="300_make_figure",
            dependencies=[config.delta_emissions.output_file],
            targets=[
                config.output_final_figure,
            ],
        ),
    ]
