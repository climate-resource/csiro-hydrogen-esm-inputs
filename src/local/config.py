"""
Configuration

Key definition of data and other implementation choices specific to this
application
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from attrs import asdict, frozen

from local.h2_adjust.timeseries import TimeseriesExtension
from local.pydoit_nb.config_discovery import (
    load_config_fragment,
    merge_config_fragments,
)
from local.serialization import FrozenDict, converter_yaml, parse_placeholders


@frozen
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

    output_directory: Path
    """
    Where to write the outputs
    """

    fast: bool
    """
    If True, grid a subset of years for speed purposes.

    Should be turned off for releases
    """


@frozen
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

    complete_file_emissions_historical: Path
    """
    File that indicates the historical emissions have been written in the input4MIPs archive
    """

    complete_file_emissions_scenario: Path
    """
    File that indicates the scenario emissions have been written in the input4MIPs archive
    """

    complete_file_concentrations: Path
    """
    File that indicates the concentrations have been written in the archive
    """


@frozen
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


@frozen
class TimeseriesOperation:
    """
    Operation to apply to a set of timeseries

    This includes filtering to select data, renaming metadata values and
    adding additional metadat
    """

    input_file: Path
    """Timeseries file"""

    filters: FrozenDict[str, Any]
    """Arguments to pass to :func:`scmdata.ScmRun.filter`"""
    renames: list[Rename] = []
    """Metadata to update in the filtered metadata"""


@frozen
class ConfigEmissions:
    """
    Configuration representing the merged set of emissions
    """

    cleaning_operations: list[TimeseriesOperation]
    """Operations to apply to `raw_scenario` to prepare it"""

    metadata: FrozenDict[str, str]
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


@frozen
class ConfigDeltaEmissionsInputs:
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


@frozen
class ConfigDeltaEmissions:
    """
    Configuration for calculating change in emissions
    """

    inputs: ConfigDeltaEmissionsInputs
    """Raw input files"""
    clean: ConfigDeltaEmissionsInputs
    """Clean and extended files"""

    energy_by_carrier: Path

    extensions: list[TimeseriesExtension]

    delta_emissions_complete: Path
    delta_emissions_totals: Path


@frozen
class ConfigBaselineH2Emissions:
    """
    Configuration for calculating the historical H2 emissions
    """

    scenario: str
    """SSP scenario from the RCMIP emissions dataset that is used for scaling"""

    baseline_source: Path
    """Source file for baseline H2 emissions"""

    anthropogenic_proxy: FrozenDict[str, str]
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


@frozen
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

    magicc_executable_path: Path
    """Path to the MAGICC executable"""

    magicc_worker_root_dir: Path
    """Root directory for MAGICC workers"""

    magicc_worker_number: int
    """Number of MAGICC workers to use"""


@frozen
class RCMIPConfig:
    """
    RCMIP paths

    Should all be replaced by bookshelf in future
    """

    concentrations_path: Path
    """Path to concentrations file"""


@frozen
class CMIP6ConcentrationsConfig:
    """CMIP6 paths and other configuration"""

    root_raw_data_dir: Path
    """Root directory for raw data"""

    concentration_scenario_ids: tuple[str, ...]
    """Scenarios to process"""

    concentration_variables: tuple[str, ...]
    """Variables to process"""


@frozen
class ConcentrationGriddingConfig:
    """Concentration gridding config"""

    cmip6_seasonality_and_latitudinal_gradient_path: Path
    """Path to CMIP6 seasonality and latitudinal gradients"""

    interim_gridded_output_dir: Path
    """
    Path to interim gridded output

    From these we write the input4MIPs style files
    """


@frozen
class ConfigSpatialEmissionsScalerTemplate:
    """Template files containing information about the scalers used"""

    input_file: Path
    """Input template file

    May contain placeholders
    """
    output_file: Path
    """Processed template file without any placeholders

    This file will later be used to generate the complete configuration used
    """


@frozen
class ConfigSpatialEmissions:
    """
    Configuration for the calculation of regional emissions
    """

    name: str
    """Name of the spatial emission run"""

    configuration_template: FrozenDict[str, Any]
    """Base configuration

    Any fields not present in :class:`spaemis.config.DownscalingScenarioConfig`
    will be ignored."""

    scaler_templates: list[ConfigSpatialEmissionsScalerTemplate]
    """Template files containing information about the scalers used

    These files may include placeholders (e.g. {ssp_scenario}) which are replaced
    when read in
    """

    scalar_template_replacements: FrozenDict[str, str]
    """Replacements to be applied to each scalar template file

    These replacements are shared for all template files"""

    downscaling_config: Path
    """Path to the generated configuration file

    This file will be able to be read in as a :class:`spaemis.config.DownscalingScenarioConfig`
    object.
    """

    proxy_directory: Path
    """Path to the proxy data

    Used for the population proxy
    """

    inventory_directory: Path
    """Path to the inventory data"""

    netcdf_output: Path
    """NetCDF output for all years, sectors and gases"""

    csv_output_directory: Path
    """CSV files matching the inventroy format"""


@frozen
class GriddingPreparationConfig:
    """
    Configuration for gridding preparation
    """

    raw_rscript: Path
    """
    Path to raw R script used for prepration
    """

    output_rscript: Path
    """
    Path to R script in the output
    """

    zenoda_data_archive: Path
    """
    Path in which results from [Feng et al. 2020](https://zenodo.org/record/2538194) have been extracted
    """

    output_dir: Path
    """
    Path in which to save the outputs
    """


@frozen
class UserPlaceholders:
    """
    Additional user-specific placeholders

    These user-specific placeholders are used for configuration that varys by
    user. For example, there maybe references to external repositories that
    are required.

    These placeholders shouldn't contain sensitive information as the contents
    will be added to the hydrated configuration. For sensitive information,
    use environment variables and ensure that the secrets aren't written to log
    output otherwise it will be available in the executed notebooks in the
    output bundle.
    """

    input4mips_local_archive: Path
    gridding_data_archive: Path
    spaemis_inventory_directory: Path
    ar6_probabilistic_distribution_file: Path
    magicc_executable_path: Path
    magicc_worker_root_dir: Path
    magicc_worker_number: int


@frozen
class Config:
    """
    Configuration class

    Used in all notebooks. This is the key communication class between our
    configuration and the notebooks and should be used for passing all
    parameters into the notebooks via papermill.
    """

    name: str
    ssp_scenario: str

    historical_notebook_dir: Path
    """Directory to store the templated historical notebooks"""

    output_notebook_dir: Path
    """Notebook output directory"""

    finalisation_notebook_dir: Path
    """Directory to store the templated finalisation notebooks"""

    gridding_preparation: GriddingPreparationConfig
    """
    Configuration for gridding preparation
    """

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

    spatial_emissions: list[ConfigSpatialEmissions]
    """Config for spatial emissions"""


@frozen
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


def load_user_placeholders_from_file(
    placeholder_file: os.PathLike[str],
) -> UserPlaceholders:
    """
    Load a set of user placeholders from disk

    Also verifies that all required values are present

    Parameters
    ----------
    placeholder_file
        User-specific placeholder file

    Returns
    -------
        Loaded placeholders
    """
    with open(placeholder_file) as fh:
        config = converter_yaml.loads(fh.read(), UserPlaceholders)

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


def get_config_bundle(
    raw_config_file: Path,
    output_root_dir: Path,
    run_id: str,
    common_config_file: Path,
    user_placeholder_file: Path,
) -> ConfigBundle:
    """
    Get config bundle from config file

    This also hydrates the config. On top of the provided parameters, it also
    fills in any ``{stub}`` placeholders in the config files.

    This function will be custom for each application as it implements all the
    specific choices about placeholders, hydration and config creation.

    .. note:
        The common and scenario configurations are merged using a recursive,
        deep merge. If the same set of configuration value is present in both
        sets of configuration the value from the scenario takes precendence.


    Parameters
    ----------
    raw_config_file
        Raw config file

        This file will contain any scenario specific configuration.

        These scenario specific configuration are merged with the common configuration
        to form a complete set of configuration. These values take precedence
        over the common configuration.


    output_root_dir
        Root directory for outputs

    run_id
        ID to use for the outputs

    common_config_file
        YAML file containing a fragment of configuration which is common for all
        sets of configuration.

    user_placeholder_file
        YAML file containing user-specific placeholders

        These user-specific parameters will be combined with placeholders from
        the CLI and the scenario. The user-specific parameters take preference
        over the scenario placeholders

    Returns
    -------
        Configuration bundle
    """
    # Make everything absolute
    output_root_dir = output_root_dir.absolute()

    # In theory you could inject whatever logic you wanted here to get the stub
    stub = raw_config_file.stem

    placeholders = dict(
        output_root_dir=output_root_dir,
        run_id=run_id,
        stub=stub,
    )

    # TODO: We probably should have a class for all placeholders
    user_placeholders = load_user_placeholders_from_file(user_placeholder_file)

    scenario_specific_config = load_config_fragment(raw_config_file)
    base_config = load_config_fragment(common_config_file)

    # The values from scenario_specific_config are used in case of a conflict
    # Note that this modifies base_config in place as well
    scenario_config_with_placeholders = merge_config_fragments(
        base_config, scenario_specific_config
    )

    # Extract any top-level string parameters to use as additional placeholders
    # This doesn't resolve recursively so each additional parameter cannot contain placeholders
    scenario_placeholders = {
        key: value
        for key, value in scenario_config_with_placeholders.items()
        if isinstance(value, str) and "{" not in value and "}" not in value
    }

    # Replace any placeholders
    # Convert back to a string temporarily for the placeholder replacement
    # Preferences the placeholders is: cli > user-specific > scenario
    scenario_config_str = parse_placeholders(
        yaml.safe_dump(scenario_config_with_placeholders),
        **scenario_placeholders,
        **asdict(user_placeholders),
        **placeholders,
    )

    # Structure the configuration
    # Any missing values will cause an exception
    config_hydrated = load_config(scenario_config_str)

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
