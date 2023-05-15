"""
Functionality related to timeseries
"""
import logging
from typing import Any

import numpy as np
import scmdata
from pyam import IamDataFrame  # type: ignore

from local.h2_adjust.constants import END_YEAR, START_YEAR

logger = logging.getLogger(__name__)


# TODO: type extension
def _apply_extension(extension: dict, run: scmdata.ScmRun) -> scmdata.ScmRun:
    # Try filter
    try:
        filtered: scmdata.ScmRun = run.filter(
            **extension["filters"], log_if_empty=False
        )
    except ValueError:
        # Invalid filters provided. Skip this extension
        filtered = scmdata.ScmRun()
    if not len(filtered):
        return run

    logger.info(f"Extending using {extension}")

    # Apply rate extension
    rate = extension.get("rate", 0)
    start_year = max(extension.get("start_year", START_YEAR), filtered["year"].min())
    if start_year not in filtered["year"].tolist():
        raise ValueError(f"{start_year} not present")  # noqa: TRY003
    end_year = extension.get("end_year", END_YEAR)

    extrapolated = filtered.interpolate(
        np.arange(str(start_year), str(end_year + 1), dtype="datetime64[Y]"),
        extrapolation_type="constant",
    ).timeseries()

    extrapolated.iloc[0, 1:] = extrapolated.iloc[0, 0:-1] * (1 + rate)
    return scmdata.ScmRun(extrapolated)


def extend(
    data: scmdata.ScmRun,
    config: Any = None,  # TODO: Is this used?
    method: str = "constant",
    start_year: int = START_YEAR,
    end_year: int = END_YEAR,
) -> scmdata.ScmRun:
    """
    Extend a timeseries in time

    Parameters
    ----------
    data
        Timeseries to extend
    method
        Default method for extending timeseries. Options are
        * "linear" (Use growth rate from last datapoints)
        * "constant" (Extend using the closest value)
    start_year
        Year which the output timeseries should start
    end_year
        Year which the output timeseries should end (inclusive)
    """
    data = scmdata.ScmRun(data.timeseries().dropna(how="all").dropna(how="all", axis=1))
    ts = data.timeseries()
    res = []

    if config:
        extensions = config["config"].get("extensions")
    else:
        extensions = []

    def _extend(df, extensions):
        clean_run = scmdata.ScmRun(df.dropna(how="all").dropna(how="all", axis=1))

        for extension in extensions:
            clean_run = _apply_extension(extension, clean_run)

        # Finally use default extrapolation
        return clean_run.interpolate(
            np.arange(str(start_year), str(end_year + 1), dtype="datetime64[Y]"),
            extrapolation_type=method,
        )

    for i in range(len(data)):
        res.append(_extend(ts.iloc[[i]], extensions))

    return scmdata.run_append(res)


def add_world_region(data: scmdata.ScmRun, method: str = "sum") -> scmdata.ScmRun:
    """
    Recalculate World totals for a given dataset

    Removes and replaces any existing ``region="World"`` data

    Parameters
    ----------
    data
        Input data with region information
    method
        Method for aggregating

    Returns
    -------
    Input data with additional ``region="World"`` sums
    """
    # Drop any existing values and recalculate
    data = data.filter(region="World", keep=False)

    world_values = data.process_over(
        "region", method, op_cols={"region": "World"}, as_run=True
    )

    return scmdata.run_append([data, world_values])


def to_pyam(run: scmdata.ScmRun) -> IamDataFrame:
    """
    Convert an ScmRun to an IamDataFrame
    """
    return run.to_iamdataframe().swap_time_for_year()
