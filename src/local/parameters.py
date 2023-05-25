"""
pydoit task parameters

Describes additional options that can be passed to the pydoit CLI and used by tasks
"""

import datetime
from pathlib import Path
from typing import Any

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

config_files_task_params: list[dict[str, Any]] = [
    {
        "name": "configdir",
        "default": Path("data") / "configuration" / "scenarios",
        "type": Path,
        "long": "configdir-scenarios",
        "help": "Path from which to load configuration for scenarios",
    },
    {
        "name": "configglob_scenarios",
        "default": "*.yaml",
        "type": str,
        "long": "configglob-scenarios",
        "help": "Glob to use when looking for configuration files for scenarios",
    },
    {
        "name": "common_configuration",
        "default": Path("data") / "configuration" / "common.yaml",
        "type": str,
        "long": "common_config",
        "help": "Common configuration used across all scenario runs",
    },
    {
        "name": "user_placeholders",
        "default": Path("data") / "configuration" / "user.yaml",
        "type": str,
        "long": "user-placeholders",
        "help": "User-specific placeholders used to hydrate the configuration",
    },
]
"""
Task parameters to use when discovering files with glob
"""
