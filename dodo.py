"""
doit configuration file
"""
import datetime
import glob
import logging
import os
import os.path
from typing import Any

from doit import task_params

from local.config import get_notebook_steps
from local.key_info import get_key_info
from local.pydoit import gen_run_notebook_tasks, get_stub, write_config_file_in_output_dir


logging.basicConfig(level=logging.INFO)


def display_key_info() -> None:
    """
    Display the project's key information
    """
    print("----")
    print(get_key_info())
    print("----")


def task_display_info() -> dict[str, Any]:
    """
    Task to display key information
    """
    return {
        "actions": [display_key_info],
        "verbosity": 2,
        "uptodate": [False],
    }


# This could be moved into some tools repository too probably
# TODO: clean up (docstring, type hints etc.)
# TODO: Split out something like
"""
from name.pydoit import get_task_crunch_scenarios

task_crunch_scenarios = get_task_crunch_scenarios(
    get_notebook_steps,
)
"""
@task_params(
    [
        {
            "name": "configdir",
            "default": os.path.join("data", "raw", "configuration"),
            "type": str,
            "long": "configdir",
            "help": "Path from which to load configuration",
        },
        {
            "name": "configglob",
            "default": "*.yaml",
            "type": str,
            "long": "configglob",
            "help": "Glob to use when looking for configuration files",
        },
        {
            "name": "output_root_dir",
            "default": os.path.join("output-bundles"),
            "type": str,
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
        {
            "name": "raw_notebooks_dir",
            "default": os.path.join("notebooks"),
            "type": str,
            "long": "raw-notebooks-dir",
            "help": "Raw notebook directory",
        },
    ]
)
def task_crunch_scenarios(
    configdir, configglob, output_root_dir, run_id, raw_notebooks_dir
) -> dict[str, Any]:
    """
    Crunch a scenario's files
    """
    # TODO, change to this pattern:
    # - discovery: find all the config files to use
    #   - tightly coupled to loading and input arguments
    # - hydration: parsing the config files and filling all the placeholders
    #   - tightly coupled to parsing and input arguments
    # - writing/serialisation: write the parsed config files back to disk in
    #   the appropriate place
    #   - should be relatively decoupled, relying only on knowing where to
    #     write the files (I guess that is tightly coupled to the input
    #     arguments)
    # - notebook task generation
    #   - this can be very dumb as it is always the same once the config is
    #     known
    #   - function like `gen_notebook_tasks(notebook_steps, configs)`
    #       - configs would be loaded from src.local and be effectively
    #         hard-coded/application specific (we could create a
    #         `generate_template` CLI or something)
    # TODO? create_configs_to_loop_over()
    output_root_dir = os.path.abspath(output_root_dir)
    config_files = glob.glob(os.path.join(configdir, configglob))
    for cf in config_files:
        # TODO: split out task_crunch_scenario
        # yield task_crunch_scenario

        # Hydrate config
        config_file_name = os.path.basename(cf)
        # HELP NEEDED: Having stub be special like this is a bit yuck but I
        # can't think of  a better way...
        stub = get_stub(config_file_name)
        config_parsed_path = os.path.join(
            output_root_dir, run_id, stub, config_file_name
        )

        # #3: If we ever want to optimise, but probably unnecessary
        parsed_config = write_config_file_in_output_dir(
            cf,
            config_parsed_path,
            output_root_dir,
            run_id,
            stub,
        )

        # Get notebook steps
        notebook_steps = get_notebook_steps(parsed_config)

        # Run the notebook steps
        yield gen_run_notebook_tasks(
            notebook_steps,
            stub=stub,
            output_notebook_dir=parsed_config.output_notebook_dir,
            config_file=config_parsed_path,
            raw_notebooks_dir=raw_notebooks_dir,
        )
