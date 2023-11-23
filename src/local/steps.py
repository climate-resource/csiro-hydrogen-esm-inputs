"""
Configuration for the steps to run

We have two sets of notebooks that are run:

* historical - Set of common steps that only need to be run once
* scenario - Set of steps that are run for each unique configuration bundle
"""
import itertools
from collections.abc import Iterable, Iterator, Sequence
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
            doc="check the inputs for the gridding proxies are all in the right place",
            notebook="000_preparation/009_prepare_for_processing_gridding",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=(config.gridding_preparation.raw_rscript,),
            targets=(
                get_checklist_file(config.gridding_preparation.zenoda_data_archive),
                config.gridding_preparation.output_rscript,
            ),
        ),
        SingleNotebookDirStep(
            doc="prepare gridding proxies from Feng et al. (2020)",
            notebook="000_preparation/010_prepare_input_data",
            raw_notebook_ext=".py",
            configuration=(config.gridding_preparation.output_dir,),
            dependencies=(
                config.gridding_preparation.output_rscript,
                get_checklist_file(config.gridding_preparation.zenoda_data_archive),
            ),
            targets=(get_checklist_file(config.gridding_preparation.output_dir),),
        ),
        SingleNotebookDirStep(
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
            doc="grid historical H2 emissions",
            notebook="100_historical_h2_emissions/120_grid_historical_emissions",
            raw_notebook_ext=".py",
            configuration=(config.historical_h2_gridding,),
            dependencies=(
                config.historical_h2_emissions.baseline_h2_emissions_countries,
                get_checklist_file(config.gridding_preparation.output_dir),
            ),
            targets=(
                get_checklist_file(config.historical_h2_gridding.output_directory),
            ),
        ),
        SingleNotebookDirStep(
            doc="write historical input4MIPS results",
            notebook="100_historical_h2_emissions/130_write_historical_input4MIPs",
            raw_notebook_ext=".py",
            configuration=(
                config.input4mips_archive.results_archive,
                config.input4mips_archive.local_archive,
                config.input4mips_archive.version,
            ),
            dependencies=(
                get_checklist_file(config.historical_h2_gridding.output_directory),
            ),
            targets=(
                get_checklist_file(historical_emissions_dir),
                config.input4mips_archive.complete_file_emissions_historical,
            ),
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
    (
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
            doc="downscale projected H2 regional emissions to countries",
            notebook="200_projected_h2_emissions/240_downscale_projected_emissions",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=(
                config.emissions.complete_scenario,
                config.historical_h2_emissions.baseline_h2_emissions_countries,
            ),
            targets=(config.emissions.complete_scenario_countries,),
        ),
        SingleNotebookDirStep(
            doc="grid projected H2 emissions",
            notebook="200_projected_h2_emissions/250_grid_projected_emissions",
            raw_notebook_ext=".py",
            configuration=(config.projected_gridding,),
            dependencies=(
                config.emissions.complete_scenario_countries,
                get_checklist_file(config.gridding_preparation.output_dir),
            ),
            targets=(get_checklist_file(config.projected_gridding.output_directory),),
        ),
        SingleNotebookDirStep(
            doc="write projected input4MIPS results",
            notebook="200_projected_h2_emissions/260_write_projected_input4MIPs",
            raw_notebook_ext=".py",
            configuration=(config.input4mips_archive,),
            dependencies=(
                get_checklist_file(config.projected_gridding.output_directory),
            ),
            targets=(config.input4mips_archive.complete_file_emissions_scenario,),
        ),
    ]

    # Only include the high production calculation step if the configuration exists
    if config.emissions.high_production:
        projected_emissions_steps.append(
            SingleNotebookDirStep(
                doc="determine the additional production emissions where "
                "Australia has a higher share of H2 production",
                notebook="200_projected_h2_emissions/270_check_production",
                raw_notebook_ext=".py",
                configuration=(config.emissions.high_production,),
                dependencies=(
                    config.emissions.complete_scenario_countries,
                    config.emissions.complete_scenario,
                ),
                targets=(config.emissions.high_production.output_file,),
            ),
        )

    concentration_gridding_steps = [
        SingleNotebookDirStep(
            doc="run MAGICC to project concentrations",
            notebook="300_projected_concentrations/310_run-magicc-for-scenarios",
            raw_notebook_ext=".py",
            configuration=(config.magicc_runs,),
            dependencies=(config.emissions.magicc_scenario,),
            targets=(config.magicc_runs.output_file,),
        ),
        # This task isn't working in a complete run under ubuntu
        # SingleNotebookDirStep(
        #     name="MAGICC - CMIP6 comparison",
        #     doc="compare MAGICC projections against CMIP6 concentrations",
        #     notebook="300_projected_concentrations/311_compare-magicc7-output-cmip6",
        #     raw_notebook_ext=".py",
        #     configuration=(config.rcmip.concentrations_path,),
        #     dependencies=(config.magicc_runs.output_file,),
        #     targets=(),
        # ),
        SingleNotebookDirStep(
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
            doc="write concentration input4MIPs style files",
            notebook="300_projected_concentrations/330_write-input4MIPs-files",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=(
                get_checklist_file(
                    config.concentration_gridding.interim_gridded_output_dir
                ),
            ),
            targets=(config.input4mips_archive.complete_file_concentrations,),
        ),
    ]

    group_name = "400_spatial_emissions"

    # Iterate over the spatial emissions setups to run
    spatial_emissions_steps = itertools.chain(
        *(
            (
                SingleNotebookDirStep(
                    name=f"{group_name}-{spatial_emis_region.name}-400_generate_configuration",
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
                    name=f"{group_name}-{spatial_emis_region.name}-410_run_projection",
                    doc="Calculate emissions for a given region",
                    notebook="400_spatial_emissions/410_run_projection",
                    raw_notebook_ext=".py",
                    configuration=(),
                    dependencies=(
                        config.input4mips_archive.complete_file_emissions_scenario,
                        spatial_emis_region.downscaling_config,
                    ),
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


def get_notebook_steps_finalise(
    configs: Iterable[Config], raw_notebooks_dir: Path, stub: str
) -> tuple[NotebookStep, ...]:
    """
    Get finalisation notebook steps

    Parameters
    ----------
    configs
        Hydrated configuration from which targets and dependencies can be
        taken. Here we are condensing so we take in multiple configurations.

    raw_notebooks_dir
        Where raw notebooks live

    stub
        Stub to identify this particular set of hydrated config, separate from
        all others

    Returns
    -------
        Finalisation notebook steps to run
    """
    dependencies_dup = itertools.chain(
        *[
            [
                c.input4mips_archive.complete_file_emissions_historical,
                c.input4mips_archive.complete_file_emissions_scenario,
                c.input4mips_archive.complete_file_concentrations,
            ]
            for c in configs
        ]
    )
    dependencies = set(dependencies_dup)

    def _get_value(func):
        values = set(func(c) for c in configs)
        if len(values) > 1:
            raise NotImplementedError()
        return list(values)[0]

    results_archive = _get_value(lambda c: c.input4mips_archive.results_archive)
    finalisation_notebook_dir = _get_value(lambda c: c.finalisation_notebook_dir)
    finalisation_data_dir = _get_value(lambda c: c.finalisation_data_dir)
    finalisation_plot_dir = _get_value(lambda c: c.finalisation_plot_dir)

    steps = [
        SingleNotebookDirStep(
            doc="Creates a checklist file based on all input4MIPs outputs",
            notebook="500_finalisation/500_write-input4MIPs-checklist",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=tuple(dependencies),
            targets=(get_checklist_file(results_archive),),
        ),
        SingleNotebookDirStep(
            doc="Generate emissions figures across all scenarios",
            notebook="500_finalisation/510_generate_emissions_figures",
            raw_notebook_ext=".py",
            configuration=(),
            dependencies=tuple(set(c.emissions.complete_scenario for c in configs)),
            targets=(
                finalisation_data_dir / "emissions_delta.csv",
                finalisation_data_dir / "emissions_total.csv",
                finalisation_data_dir / "energy_by_carrier.csv",
                finalisation_plot_dir / "total_emissions.pdf",
                finalisation_plot_dir / "emissions_by_carrier.pdf",
                finalisation_plot_dir / "emissions_by_region.pdf",
                finalisation_plot_dir / "emissions_by_sector.pdf",
                finalisation_plot_dir / "energy_by_carrier.pdf",
                finalisation_plot_dir / "energy_by_region.pdf",
            ),
        ),
    ]

    out = tuple(
        sds.to_notebook_step(
            raw_notebooks_dir=raw_notebooks_dir,
            output_notebook_dir=finalisation_notebook_dir,
            stub=stub,
        )
        for sds in steps
    )

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


def gen_finalise_tasks(
    config_bundles: Sequence[ConfigBundle],
    raw_notebooks_dir: Path,
) -> Iterator[dict[str, Any]]:
    """
    Generate finalisation tasks

    This only creates one finalisation task, even though there are multiple
    scenarios captured by ``config_bundles``.

    Parameters
    ----------
    config_bundles
        Collection of configuration bundle to be run

    raw_notebooks_dir
        Where raw notebooks live

    Yields
    ------
        Tasks to run with pydoit
    """
    notebook_steps = get_notebook_steps_finalise(
        [cb.config_hydrated for cb in config_bundles],
        raw_notebooks_dir,
        # Hard-coding might actually be the right choice here
        stub="finalise",
    )

    # Doesn't matter which config you use, results are all the same
    yield from gen_run_notebook_tasks(
        notebook_steps,  # type: ignore
        config_bundles[0].config_hydrated_path,
    )
