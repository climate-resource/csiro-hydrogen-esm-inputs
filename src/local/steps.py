"""
Configuration for the steps to run

We have two sets of notebooks that are run:

* historical - Set of common steps that only need to be run once
* scenario - Set of steps that are run for each unique configuration bundle
"""
import itertools
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from local.config import Config, ConfigBundle
from local.pydoit_nb.checklist import get_checklist_file
from local.pydoit_nb.gen_notebook_tasks import gen_run_notebook_tasks
from local.pydoit_nb.notebooks import NotebookStep, SingleNotebookDirStep


def get_notebook_steps_historical(
    config: Config, raw_notebooks_dir: Path, stub: str
) -> tuple[NotebookStep, ...]:
    """
    Get historical notebook steps

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
        Historical notebook steps to run
    """
    historical_emissions_dir = (
        config.input4mips_archive.results_archive
        / "input4MIPs"
        / "CMIP6"
        / "CMIP"
        / "CR"
        / "CR-historical"
    )

    steps = [
        SingleNotebookDirStep(
            name="Download CMIP6 concentrations",
            doc="download required CMIP6 concentrations",
            notebook="300_projected_concentrations/320_download-cmip6-data",
            raw_notebook_ext=".py",
            configuration=(config.cmip6_concentrations,),
            dependencies=(),
            targets=(
                get_checklist_file(config.cmip6_concentrations.root_raw_data_dir),
            ),
        ),
        SingleNotebookDirStep(
            name="calculate baseline historical emissions",
            doc="calculate baseline historical emissions",
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
            doc="downscale historical H2 regional emissions to countries",
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
            doc="grid historical H2 emissions",
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
            doc="write historical input4MIPS results",
            notebook="100_historical_h2_emissions/130_write_historical_input4MIPs",
            raw_notebook_ext=".py",
            configuration=(config.input4mips_archive,),
            dependencies=(
                get_checklist_file(config.historical_h2_gridding.output_directory),
            ),
            targets=(get_checklist_file(historical_emissions_dir),),
        ),
    ]

    out = tuple(
        sds.to_notebook_step(
            raw_notebooks_dir=raw_notebooks_dir,
            output_notebook_dir=config.historical_notebook_dir,
            stub=stub,
        )
        for sds in steps
    )

    return out


def get_notebook_steps_scenario(
    config: Config, raw_notebooks_dir: Path, stub: str
) -> list[NotebookStep]:
    """
    Get notebook steps for a given scenario

    This defines all of the scenario-specific notebooks that are involved in
    workflow.

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
    projected_emissions_dir = (
        config.input4mips_archive.results_archive
        / "input4MIPs"
        / "CMIP6"
        / "ScenarioMIP"
        / "CR"
        / f"CR-{config.name}"
    )

    # Projected Emissions steps
    projected_emissions_steps = [
        SingleNotebookDirStep(
            name="create the input emissions scenario",
            doc="create the input emissions scenario",
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
            doc="extend input data to cover target period",
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
            doc="calculate delta emissions from H2 usage",
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
            doc="calculate baseline projected emissions",
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
            doc="merge projected emissions to form a scenario",
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
            doc="downscale projected H2 regional emissions to countries",
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
            doc="grid projected H2 emissions",
            notebook="200_projected_h2_emissions/250_grid_projected_emissions",
            raw_notebook_ext=".py",
            configuration=(config.projected_gridding,),
            dependencies=(config.emissions.complete_scenario_countries,),
            targets=(get_checklist_file(config.projected_gridding.output_directory),),
        ),
        SingleNotebookDirStep(
            name="write projected input4MIPS results",
            doc="write projected input4MIPS results",
            notebook="200_projected_h2_emissions/260_write_projected_input4MIPs",
            raw_notebook_ext=".py",
            configuration=(config.input4mips_archive,),
            dependencies=(
                get_checklist_file(config.projected_gridding.output_directory),
            ),
            targets=(get_checklist_file(projected_emissions_dir),),
        ),
    ]

    concentration_gridding_steps = [
        SingleNotebookDirStep(
            name="MAGICC run",
            doc="run MAGICC to project concentrations",
            notebook="300_projected_concentrations/310_run-magicc-for-scenarios",
            raw_notebook_ext=".py",
            configuration=(config.magicc_runs,),
            dependencies=(config.emissions.magicc_scenario,),
            targets=(config.magicc_runs.output_file,),
        ),
        SingleNotebookDirStep(
            name="MAGICC - CMIP6 comparison",
            doc="compare MAGICC projections against CMIP6 concentrations",
            notebook="300_projected_concentrations/311_compare-magicc7-output-cmip6",
            raw_notebook_ext=".py",
            configuration=(config.rcmip.concentrations_path,),
            dependencies=(config.magicc_runs.output_file,),
            targets=(),
        ),
        SingleNotebookDirStep(
            name="Extract CMIP6 grids",
            doc="extract grids from CMIP6 concentrations",
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
            name="Grided projections",
            doc="create gridded concentration projections",
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
            name="Write input4MIPs concentrations",
            doc="write concentration input4MIPs style files",
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

    # Iterate over the spatial emissions setups to run
    spatial_emissions_steps = itertools.chain(
        *(
            (
                SingleNotebookDirStep(
                    name=f"spaemis - {spatial_emis_region.name} - generate scaler configuration",
                    doc="Combines different templates for scalers together",
                    notebook="400_spatial_emissions/400_generate_configuration",
                    raw_notebook_ext=".py",
                    configuration=(spatial_emis_region,),
                    dependencies=tuple(
                        template.input_file
                        for template in spatial_emis_region.scaler_templates
                    ),
                    targets=(spatial_emis_region.downscaling_config,),
                    notebook_suffix=spatial_emis_region.name,
                    notebook_parameters={"name": spatial_emis_region.name},
                ),
                SingleNotebookDirStep(
                    name=f"spaemis - {spatial_emis_region.name} - calculate projections for a region",
                    doc="Calculate emissions for a given region",
                    notebook="400_spatial_emissions/410_run_projection",
                    raw_notebook_ext=".py",
                    configuration=(),
                    dependencies=(spatial_emis_region.downscaling_config,),
                    targets=(
                        get_checklist_file(spatial_emis_region.csv_output_directory),
                        spatial_emis_region.netcdf_output,
                    ),
                    notebook_suffix=spatial_emis_region.name,
                    notebook_parameters={"name": spatial_emis_region.name},
                ),
            )
            for spatial_emis_region in config.spatial_emissions
        )
    )
    out = [
        sds.to_notebook_step(
            raw_notebooks_dir=raw_notebooks_dir,
            output_notebook_dir=config.output_notebook_dir,
            stub=stub,
        )
        for sds in [
            *projected_emissions_steps,
            *concentration_gridding_steps,
            *spatial_emissions_steps,
        ]
    ]

    return out


def gen_crunch_scenario_tasks(
    config_bundles: Sequence[ConfigBundle], raw_notebooks_dir: Path
) -> Iterator[dict[str, Any]]:
    """
    Generate crunch scenario tasks

    Parameters
    ----------
    config_bundles
        Configuration bundle

    raw_notebooks_dir
        Where raw notebooks live

    Yields
    ------
        Tasks to run with pydoit
    """
    for cb in config_bundles:
        notebook_steps = get_notebook_steps_scenario(
            cb.config_hydrated,
            raw_notebooks_dir,
            stub=cb.stub,
        )

        yield from gen_run_notebook_tasks(
            notebook_steps,  # type: ignore
            cb.config_hydrated_path,
        )


def gen_crunch_historical_tasks(
    config_bundles: Sequence[ConfigBundle],
    raw_notebooks_dir: Path,
) -> Iterator[dict[str, Any]]:
    """
    Generate historical crunching tasks

    This avoids clashes if multiple scenarios have the same historical tasks.
    There is an assumption that the scenarios share a common historical
    configuration. If any of the scenarios have different historical configuration
    an exception will be raised.

    Parameters
    ----------
    config_bundles
        Collection of configuration bundle to be run

        Each configuration bundle is a different scenario, but we expect that
        they all have the same historical configuration.

    raw_notebooks_dir
        Where raw notebooks live

    Yields
    ------
        Tasks to run with pydoit
    """
    notebook_steps = [
        get_notebook_steps_historical(
            cb.config_hydrated,
            raw_notebooks_dir,
            # Hard-coding might actually be the right choice here
            stub="historical",
        )
        for cb in config_bundles
    ]

    common_steps = set(notebook_steps)
    if len(common_steps) != 1:
        raise NotImplementedError

    # Doesn't matter which config you use, results are all the same
    yield from gen_run_notebook_tasks(
        notebook_steps[0],  # type: ignore
        config_bundles[0].config_hydrated_path,
    )
