"""
Configuration

Key definition of data and other implementation choices specific to this
application
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from attrs import define

from local.h2_adjust.timeseries import TimeseriesExtension
from local.pydoit_nb.checklist import get_checklist_file
from local.pydoit_nb.gen_notebook_tasks import gen_run_notebook_tasks
from local.pydoit_nb.notebooks import NotebookStep, SingleNotebookDirStep
from local.serialization import converter_yaml, parse_placeholders


@define
class ConfigGridding:
    """
    Configuration for gridding a set of emissions
    """

    proxy_mapping: Path
    """
    CSV file containing the proxies used for gridding a given gas and sector
    """

    seasonality_mapping: Path
    """
    CSV file containing the source of the seasonality information for each gas and
    sector
    """

    sector_type: Literal["CEDS9"]
    """Type of CEDS sectors used for gridding"""

    grid_data_directory: Path
    """
    Pre-processed data for gridding

    TODO: write more docs

    See https://github.com/lewisjared/aneris/blob/feng/notebooks/gridding/010_prepare_input_data.py
    """
    output_directory: Path
    """
    Where to write the outputs
    """

    fast: bool
    """
    If True, grid a subset of years for speed purposes.

    Should be turned off for releases
    """


@define
class ConfigInput4MIPs:
    """
    Configuration for handling a local archive of input4MIPs data
    """

    local_archive: Path
    """
    Directory containing pre-downloaded input4MIPs data
    """

    results_archive: Path
    """
    Output directory for the results
    """

    version: str
    """
    Version flag for the generated results
    """


@define
class Rename:
    """
    Configuration for a renaming operation

    Akin to a :func:`scmdata.ScmRun.set_meta`
    """

    dimension: str
    """Dimension to affect"""
    target: str
    """Existing value

    To select the entire column use '*'
    """
    to: str
    """New value"""


@define
class TimeseriesOperation:
    """
    Operation to apply to a set of timeseries

    This includes filtering to select data, renaming metadata values and
    adding additional metadat
    """

    input_file: Path
    """Timeseries file"""

    filters: dict[str, Any]
    """Arguments to pass to :func:`scmdata.ScmRun.filter`"""
    renames: list[Rename] = []
    """Metadata to update in the filtered metadata"""


@define
class ConfigEmissions:
    """
    Configuration representing the merged set of emissions
    """

    cleaning_operations: list[TimeseriesOperation]
    """Operations to apply to `raw_scenario` to prepare it"""

    metadata: dict[str, str]
    """Additional dimensions to update for the cleaned set of timeseries"""

    input_scenario: Path
    """
    Input emissions scenario

    This is the raw scenario after the cleaning operations have been performed
    """

    complete_scenario: Path
    """
    A complete set of emissions including H2

    This is the key output from D2
    """

    magicc_scenario: Path
    """
    Emissions scenario formatted for use by MAGICC
    """

    complete_scenario_countries: Path

    figure_by_sector: Path
    figure_by_sector_only_modified: Path
    figure_vs_rcmip: Path


@define
class ConfigDataEmissionsInputs:
    """
    Input files for calculating the change in emissions

    # TODO: Document what exactually is expected in these files
    """

    share_by_carrier: Path
    """Shares of each carrier fuel"""
    leakage_rates: Path
    """Leakage rate for each sector/gas"""

    emissions_intensities_production: Path
    """Emissions intensities from the production of an H2 Fuel source"""
    emissions_intensities_combustion: Path
    """Emissions intensities from the combustion of H2-related fuels"""


@define
class ConfigDeltaEmissions:
    """
    Configuration for calculating change in emissions
    """

    inputs: ConfigDataEmissionsInputs
    """Raw input files"""
    clean: ConfigDataEmissionsInputs
    """Clean and extended files"""

    energy_by_carrier: Path

    extensions: list[TimeseriesExtension]

    delta_emissions_complete: Path
    delta_emissions_totals: Path


@define
class ConfigBaselineH2Emissions:
    """
    Configuration for calculating the historical H2 emissions
    """

    scenario: str
    """SSP scenario from the RCMIP emissions dataset that is used for scaling"""

    baseline_source: Path
    """Source file for baseline H2 emissions"""

    anthropogenic_proxy: dict[str, str]
    """
    Proxy to provide the sectoral and regional information for a given source of H2 emissions

    Keys represent a mechanism of H2 emissions (variables defined by the study into baseline emissions
    :attr:`baseline_source`, for example "Emissions|H2|Biomass burning".

    The values map to a CEDs variable from which the regional and sectoral information will be
    sourced.
    """

    # Data
    baseline_h2_emissions_regions: Path
    """
    Calculated baseline H2 emissions, by gas, by sector and by region
    """

    baseline_h2_emissions_countries: Path
    """
    Calculated historical emissions downscaled to each country
    """

    # Figures
    figure_baseline_by_sector: Path
    figure_baseline_by_source: Path
    figure_baseline_by_source_and_sector: Path


@define
class ConfigMAGICCRuns:
    """
    Configuration for running MAGICC to produce updated concentration projections
    """

    n_cfgs_to_run: int
    """
    Number of configurations to run

    Should be 600 for a production run
    """

    output_file: Path
    """Where to save the output of the MAGICC runs"""

    ar6_probabilistic_distribution_file: Path
    """
    Path to the AR6 probabilistic distribution file

    This file isn't tracked by Git.

    TODO: add download instructions to README
    """

    test_scenario: Path
    """
    Path to test scenario

    TODO: delete this once we hook everything up together, use
    ``config.emissions.complete_scenario`` instead
    """

    magicc_executable_path: Path
    """Path to the MAGICC executable"""

    magicc_worker_root_dir: Path
    """Root directory for MAGICC workers"""

    magicc_worker_number: int
    """Number of MAGICC workers to use"""


@define
class RCMIPConfig:
    """
    RCMIP paths

    Should all be replaced by bookshelf in future
    """

    concentrations_path: Path
    """Path to concentrations file"""


@define
class CMIP6ConcentrationsConfig:
    """CMIP6 paths and other configuration"""

    root_raw_data_dir: Path
    """Root directory for raw data"""

    concentration_scenario_ids: list[str]
    """Scenarios to process"""

    concentration_variables: list[str]
    """Variables to process"""


@define
class ConcentrationGriddingConfig:
    """Concentration gridding config"""

    cmip6_seasonality_and_latitudinal_gradient_path: Path
    """Path to CMIP6 seasonality and latitudinal gradients"""

    interim_gridded_output_dir: Path
    """
    Path to interim gridded output

    From these we write the input4MIPs style files
    """

    gridded_output_dir: Path
    """Path to gridded output, written in input4MIPs style"""


@define
class Config:
    """
    Configuration class

    Used in all notebooks. This is the key communication class between our
    configuration and the notebooks and should be used for passing all
    parameters into the notebooks via papermill.
    """

    name: str
    ssp_scenario: str

    output_notebook_dir: Path
    """Notebook output directory"""

    emissions: ConfigEmissions
    """
    Configuration related to the emissions scenarios
    """

    historical_h2_emissions: ConfigBaselineH2Emissions
    """Configuration for calculating the baseline H2 emissions from existing industries"""

    historical_h2_gridding: ConfigGridding
    """Configuration for the gridding of the historical H2 emissions"""

    input4mips_archive: ConfigInput4MIPs
    """
    Configuration for an archive of input4MIPs data

    The required data depends on which parts of the process that are intended to run.

    # TODO: document the list of variables and scenarios required. X_em_anthro
    X_em_AIR_anthro for IAMC-IMAGE-ssp119-1-1, IAMC-IMAGE-ssp126-1-1 and IAMC-MESSAGE-GLOBIOM-ssp245-1-1
    """

    delta_emissions: ConfigDeltaEmissions
    """Configuration for calculating the change in emissions"""

    projected_h2_emissions: ConfigBaselineH2Emissions
    """Configuration for calculating the baseline H2 emissions from existing industries"""

    projected_gridding: ConfigGridding
    """Configuration for the gridding of the the modified projected emissions"""

    magicc_runs: ConfigMAGICCRuns
    """Configuration for running MAGICC"""

    rcmip: RCMIPConfig
    """Configuration of RCMIP paths"""

    cmip6_concentrations: CMIP6ConcentrationsConfig
    """Configuration of CMIP6 concentrations requirements"""

    concentration_gridding: ConcentrationGriddingConfig
    """Config for concentration gridding"""


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


# Hmmm somehow passing doesn't work perfectly to allow e.g.
# ``poetry run doit run "crunch_scenarios:Run MAGICC to project concentrations_ssp119-low" --run-id zn-test``
# In this case, the default run-id is used. I think it is because the
# parameters are passed to the subtask, not the task
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
        # TODO: revert this to "default": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "default": "zn-test",
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
    historical_emissions_dir = (
        config.input4mips_archive.results_archive
        / "input4MIPs"
        / "CMIP6"
        / "CMIP"
        / "CR"
        / "CR-historical"
    )
    projected_emissions_dir = (
        config.input4mips_archive.results_archive
        / "input4MIPs"
        / "CMIP6"
        / "ScenarioMIP"
        / "CR"
        / f"CR-{config.name}"
    )

    # TODO: refactor into separate file
    historical_baseline_emissions = [
        SingleNotebookDirStep(
            name="calculate baseline historical emissions",
            notebook="100_historical_h2_emissions/100_calculate_historical_anthropogenic",
            raw_notebook_ext=".py",
            configuration=(
                config.historical_h2_emissions.baseline_source,
                config.historical_h2_emissions.anthropogenic_proxy,
            ),
            dependencies=(config.historical_h2_emissions.baseline_source,),
            targets=(
                config.historical_h2_emissions.baseline_h2_emissions_regions,
                config.historical_h2_emissions.figure_baseline_by_source,
                config.historical_h2_emissions.figure_baseline_by_sector,
                config.historical_h2_emissions.figure_baseline_by_source_and_sector,
            ),
        ),
        SingleNotebookDirStep(
            name="downscale historical H2 regional emissions to countries",
            notebook="100_historical_h2_emissions/110_downscale_historical_emissions",
            raw_notebook_ext=".py",
            configuration=(),  # No extra configuration dependencies
            dependencies=(
                config.historical_h2_emissions.baseline_h2_emissions_regions,
            ),
            targets=(config.historical_h2_emissions.baseline_h2_emissions_countries,),
        ),
        SingleNotebookDirStep(
            name="grid historical H2 emissions",
            notebook="100_historical_h2_emissions/120_grid_historical_emissions",
            raw_notebook_ext=".py",
            configuration=(config.historical_h2_gridding,),
            dependencies=(
                config.historical_h2_emissions.baseline_h2_emissions_countries,
            ),
            targets=(
                get_checklist_file(config.historical_h2_gridding.output_directory),
            ),
        ),
        SingleNotebookDirStep(
            name="write historical input4MIPS results",
            notebook="100_historical_h2_emissions/130_write_historical_input4MIPs",
            raw_notebook_ext=".py",
            configuration=(config.input4mips_archive,),
            dependencies=(
                get_checklist_file(config.historical_h2_gridding.output_directory),
            ),
            targets=(get_checklist_file(historical_emissions_dir),),
        ),
    ]

    # Projected Emissions steps
    projected_emissions = [
        SingleNotebookDirStep(
            name="create the input emissions scenario",
            notebook="200_projected_h2_emissions/200_make_input_scenario",
            raw_notebook_ext=".py",
            configuration=(
                config.emissions.cleaning_operations,
                config.emissions.metadata,
            ),
            dependencies=tuple(
                set(op.input_file for op in config.emissions.cleaning_operations)
            ),
            targets=(config.emissions.input_scenario,),
        ),
        SingleNotebookDirStep(
            name="extend input data to cover target period",
            notebook="200_projected_h2_emissions/201_extend_timeseries",
            raw_notebook_ext=".py",
            configuration=(config.delta_emissions.extensions,),
            dependencies=(
                config.emissions.input_scenario,
                config.delta_emissions.inputs.share_by_carrier,
                config.delta_emissions.inputs.emissions_intensities_production,
                config.delta_emissions.inputs.emissions_intensities_combustion,
                config.delta_emissions.inputs.leakage_rates,
            ),
            targets=(
                config.delta_emissions.energy_by_carrier,
                config.delta_emissions.clean.share_by_carrier,
                config.delta_emissions.clean.emissions_intensities_production,
                config.delta_emissions.clean.emissions_intensities_combustion,
                config.delta_emissions.clean.leakage_rates,
            ),
        ),
        SingleNotebookDirStep(
            name="calculate delta emissions from H2 usage",
            notebook="200_projected_h2_emissions/210_calculate_delta_emissions",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=(
                config.delta_emissions.energy_by_carrier,
                config.delta_emissions.clean.share_by_carrier,
                config.delta_emissions.clean.emissions_intensities_production,
                config.delta_emissions.clean.emissions_intensities_combustion,
                config.delta_emissions.clean.leakage_rates,
            ),
            targets=(
                config.delta_emissions.delta_emissions_complete,
                config.delta_emissions.delta_emissions_totals,
            ),
        ),
        SingleNotebookDirStep(
            name="calculate baseline projected emissions",
            notebook="200_projected_h2_emissions/220_calculate_baseline_anthropogenic",
            raw_notebook_ext=".py",
            configuration=(config.projected_h2_emissions,),
            dependencies=(config.projected_h2_emissions.baseline_source,),
            targets=(
                config.projected_h2_emissions.baseline_h2_emissions_regions,
                config.projected_h2_emissions.figure_baseline_by_source,
                config.projected_h2_emissions.figure_baseline_by_sector,
                config.projected_h2_emissions.figure_baseline_by_source_and_sector,
            ),
        ),
        SingleNotebookDirStep(
            name="merge projected emissions to form a scenario",
            notebook="200_projected_h2_emissions/230_merge_emissions",
            raw_notebook_ext=".py",
            configuration=(
                config.name,
                config.ssp_scenario,
            ),
            dependencies=(
                config.emissions.input_scenario,
                config.delta_emissions.delta_emissions_complete,
                config.projected_h2_emissions.baseline_h2_emissions_regions,
            ),
            targets=(
                config.emissions.complete_scenario,
                config.emissions.magicc_scenario,
                # Figures
                config.emissions.figure_by_sector,
                config.emissions.figure_by_sector_only_modified,
                config.emissions.figure_vs_rcmip,
            ),
        ),
        SingleNotebookDirStep(
            name="downscale projected H2 regional emissions to countries",
            notebook="200_projected_h2_emissions/240_downscale_projected_emissions",
            raw_notebook_ext=".py",
            configuration=(
                config.historical_h2_emissions.baseline_h2_emissions_countries,
            ),
            dependencies=(config.emissions.complete_scenario,),
            targets=(config.emissions.complete_scenario_countries,),
        ),
        SingleNotebookDirStep(
            name="grid projected H2 emissions",
            notebook="200_projected_h2_emissions/250_grid_projected_emissions",
            raw_notebook_ext=".py",
            configuration=(config.projected_gridding,),
            dependencies=(config.emissions.complete_scenario_countries,),
            targets=(get_checklist_file(config.projected_gridding.output_directory),),
        ),
        SingleNotebookDirStep(
            name="write projected input4MIPS results",
            notebook="200_projected_h2_emissions/260_write_projected_input4MIPs",
            raw_notebook_ext=".py",
            configuration=(config.input4mips_archive,),
            dependencies=(
                get_checklist_file(config.projected_gridding.output_directory),
            ),
            targets=(get_checklist_file(projected_emissions_dir),),
        ),
        SingleNotebookDirStep(
            name="run MAGICC to project concentrations",
            notebook="300_projected_concentrations/310_run-magicc-for-scenarios",
            raw_notebook_ext=".py",
            configuration=(config.magicc_runs,),
            dependencies=(
                config.magicc_runs.test_scenario,
                # TODO: switch to
                # config.emissions.complete_scenario,
            ),
            targets=(config.magicc_runs.output_file,),
        ),
        SingleNotebookDirStep(
            name="compare MAGICC projections against CMIP6 concentrations",
            notebook="300_projected_concentrations/311_compare-magicc7-output-cmip6_concentrations",
            raw_notebook_ext=".py",
            configuration=(config.rcmip.concentrations_path,),
            dependencies=(config.magicc_runs.output_file,),
            targets=(),
        ),
        SingleNotebookDirStep(
            name="download required CMIP6 concentrations",
            notebook="300_projected_concentrations/320_download-cmip6-data",
            raw_notebook_ext=".py",
            configuration=(config.cmip6_concentrations,),
            dependencies=(),
            targets=(
                get_checklist_file(config.cmip6_concentrations.root_raw_data_dir),
            ),
        ),
        SingleNotebookDirStep(
            name="extract grids from CMIP6 concentrations",
            notebook="300_projected_concentrations/321_extract-grids-from-cmip6",
            raw_notebook_ext=".py",
            configuration=(
                config.cmip6_concentrations.concentration_scenario_ids,
                config.cmip6_concentrations.concentration_variables,
            ),
            dependencies=(
                get_checklist_file(config.cmip6_concentrations.root_raw_data_dir),
            ),
            targets=(
                config.concentration_gridding.cmip6_seasonality_and_latitudinal_gradient_path,
            ),
        ),
        SingleNotebookDirStep(
            name="create gridded concentration projections",
            notebook="300_projected_concentrations/322_projection-gridding",
            raw_notebook_ext=".py",
            configuration=(config.cmip6_concentrations.concentration_variables,),
            dependencies=(
                config.concentration_gridding.cmip6_seasonality_and_latitudinal_gradient_path,
                config.rcmip.concentrations_path,
                config.magicc_runs.output_file,
            ),
            targets=(
                get_checklist_file(
                    config.concentration_gridding.interim_gridded_output_dir
                ),
            ),
        ),
        SingleNotebookDirStep(
            name="write concentration input4MIPs style files",
            notebook="300_projected_concentrations/330_write-input4MIPs-files",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=(
                get_checklist_file(
                    config.concentration_gridding.interim_gridded_output_dir
                ),
            ),
            targets=(
                get_checklist_file(config.concentration_gridding.gridded_output_dir),
            ),
        ),
    ]

    single_dir_steps = [*historical_baseline_emissions, *projected_emissions]

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
