"""
Configuration

Key definition of data and other implementation choices specific to this
application
"""
from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from attrs import define

from local.pydoit_nb.gen_notebook_tasks import gen_run_notebook_tasks
from local.pydoit_nb.notebooks import NotebookStep, SingleNotebookDirStep
from local.serialization import converter_yaml, parse_placeholders


@define
class ConfigDeltaEmissions:
    """
    Configuration for calculating change in emissions
    """

    input_file: Path
    """Input file"""

    output_file: Path
    """Output file"""


@define
class ConfigAnthroBaseline:
    """
    Configuration for calculating anthropogenic baseline emissions
    """

    input_file: Path
    """Input file"""


@define
class Config:
    """
    Configuration class

    Used in all notebooks. This is the key communication class between our
    configuration and the notebooks and should be used for passing all
    parameters into the notebooks via papermill.
    """

    output_notebook_dir: Path
    """Notebook output directory"""

    delta_emissions: ConfigDeltaEmissions
    """Configuration for calculating the change in emissions"""

    anthro_baseline: ConfigAnthroBaseline
    """Configuration for calculating the change in anthropogenic baseline"""

    output_final_figure: Path
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
    with open(config_file) as fh:
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


config_task_params: list[dict[str, Any]] = [
    {
        "name": "output_root_dir",
        "default": Path("output-bundles"),
        "type": Path,
        "long": "output-root-dir",
        "help": "Root directory for outputs",
    },
    {
        "name": "run_id",
        "default": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "type": str,
        "long": "run-id",
        "help": "id for the outputs",
    },
]
"""
Task parameters to use to support generating config bundles
"""


@define
class ConfigBundle:
    """
    Configuration bundle

    Useful to have everything in one place once we have finished hydrating
    config, setting paths etc.
    """

    raw_config_file: Path
    """Path to raw configuration on which this bundle is based"""

    config_hydrated: Config
    """Hydrated config"""

    config_hydrated_path: Path
    """Path in/from which to read/write ``config_hydrated``"""

    output_root_dir: Path
    """Root output directory"""
    # Could add validation here that this is an absolute path and exists

    run_id: str
    """ID for the run"""

    stub: str
    """Stub to identify this particular set of hydrated config, separate from all others"""


def get_config_bundle(
    raw_config_file: Path,
    output_root_dir: Path,
    run_id: str,
) -> ConfigBundle:
    """
    Get config bundle from config file

    This also hydrates the config. On top of the provided parameters, it also
    fills in any ``{stub}`` placeholders in the config files.

    This function will be custom for each application as it implements all the
    specific choices about placeholders, hydration and config creation.

    Parameters
    ----------
    raw_config_file
        Raw config file

    output_root_dir
        Root directory for outputs

    run_id
        ID to use for the outputs

    Returns
    -------
        Configuration bundle
    """
    # Make everything absolute
    output_root_dir = output_root_dir.absolute()

    # In theory you could inject whatever logic you wanted here to get the stub
    stub = raw_config_file.stem

    # Parse placeholders
    with open(raw_config_file) as fh:
        loaded_str = fh.read()

    loaded_str_parsed = parse_placeholders(
        loaded_str,
        output_root_dir=output_root_dir,
        run_id=run_id,
        stub=stub,
    )

    config_hydrated = load_config(loaded_str_parsed)

    #
    config_hydrated_path = output_root_dir / run_id / stub / raw_config_file.name
    config_hydrated_path.parent.mkdir(parents=True, exist_ok=True)

    return ConfigBundle(
        config_hydrated=config_hydrated,
        config_hydrated_path=config_hydrated_path,
        output_root_dir=output_root_dir,
        run_id=run_id,
        stub=stub,
        raw_config_file=raw_config_file,
    )


def write_config_file_in_output_dir(cb: ConfigBundle) -> None:
    """
    Write config file in output directory

    Parameters
    ----------
    cb
        Config bundle
    """
    with open(cb.config_hydrated_path, "w") as fh:
        fh.write(converter_yaml.dumps(cb.config_hydrated))


notebook_step_task_params: list[dict[str, Any]] = [
    {
        "name": "raw_notebooks_dir",
        "default": Path("notebooks"),
        "type": str,
        "long": "raw-notebooks-dir",
        "help": "Raw notebook directory",
    },
]
"""
Task parameters to use to support generating notebook steps
"""


def get_notebook_steps(
    config: Config, raw_notebooks_dir: Path, stub: str
) -> list[NotebookStep]:
    """
    Get notebook steps

    This essentially defines the configuration of our entire workflow

    Parameters
    ----------
    config
        Hydrated configuration from which targets and dependencies can be
        taken

    raw_notebooks_dir
        Where raw notebooks live

    stub
        Stub to identify this particular set of hydrated config, separate from
        all others

    Returns
    -------
        Notebook steps to run
    """
    single_dir_steps = [
        SingleNotebookDirStep(
            name="make input files",
            notebook="000_make_input_files",
            raw_notebook_ext=".py",
            dependencies=tuple(),
            targets=(
                config.delta_emissions.input_file,
                config.anthro_baseline.input_file,
            ),
        ),
        SingleNotebookDirStep(
            name="calculate delta emissions",
            notebook="200_calculate_delta_emissions",
            raw_notebook_ext=".py",
            dependencies=(config.delta_emissions.input_file,),
            targets=(config.delta_emissions.output_file,),
        ),
        SingleNotebookDirStep(
            name="create final figure",
            notebook="300_make_figure",
            raw_notebook_ext=".py",
            dependencies=(config.delta_emissions.output_file,),
            targets=(config.output_final_figure,),
        ),
    ]

    out = [
        sds.to_notebook_step(
            raw_notebooks_dir=raw_notebooks_dir,
            output_notebook_dir=config.output_notebook_dir,
            stub=stub,
        )
        for sds in single_dir_steps
    ]

    return out


def gen_crunch_scenario_tasks(
    config_bundle: ConfigBundle, raw_notebooks_dir: Path
) -> Iterator[dict[str, Any]]:
    """
    Generate crunch scenario tasks

    Parameters
    ----------
    config_bundle
        Configuration bundle

    raw_notebooks_dir
        Where raw notebooks live

    Yields
    ------
        Tasks to run with pydoit
    """
    notebook_steps = get_notebook_steps(
        config_bundle.config_hydrated, raw_notebooks_dir, stub=config_bundle.stub
    )

    return gen_run_notebook_tasks(
        notebook_steps,
        config_bundle.config_hydrated_path,
    )
