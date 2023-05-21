"""
Functionality related to timeseries
"""
import logging
from typing import Any

import numpy as np
import pandas as pd
import scmdata
from attrs import define
from pyam import IamDataFrame  # type: ignore

from local.h2_adjust.constants import END_YEAR, START_YEAR

logger = logging.getLogger(__name__)


@define
class TimeseriesExtension:
    """
    Extend a set of timeseries using a rate of change
    """

    filters: dict[str, Any]
    """Filter arguments for the timeseries to be extended"""
    rate: float
    """Annual percentage change to apply to the timeseries

    0 is no change. Negative decreases, positive increases
    """
    start_year: int
    """Start year of the extension"""
    end_year: int
    """When to stop applying the extension"""


def _apply_extension(
    extension: TimeseriesExtension, run: scmdata.ScmRun
) -> scmdata.ScmRun:
    # Try filter
    try:
        filtered: scmdata.ScmRun = run.filter(**extension.filters, log_if_empty=False)
    except ValueError:
        # Invalid filters provided. Skip this extension
        filtered = scmdata.ScmRun()
    if not len(filtered):
        return run

    logger.info(f"Extending using {extension}")

    # Apply rate extension
    start_year = max(
        extension.start_year,
        filtered["year"].min(),
    )
    if start_year not in filtered["year"].tolist():
        raise ValueError(f"{start_year} not present")  # noqa: TRY003
    end_year = extension.end_year

    extrapolated = filtered.interpolate(
        np.arange(str(start_year), str(end_year + 1), dtype="datetime64[Y]"),
        extrapolation_type="constant",
    ).timeseries()

    extrapolated.iloc[0, 1:] = extrapolated.iloc[0, 0:-1] * (1 + extension.rate)
    return scmdata.ScmRun(extrapolated)


def extend(
    data: scmdata.ScmRun,
    extensions: list[TimeseriesExtension],
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
    extensions
        Custom extensions to apply to a subset of data
    method
        Default method for extending timeseries. Options are
        * "linear" (Use growth rate from last datapoints)
        * "constant" (Extend using the closest value)
    start_year
        Year which the output timeseries should start
    end_year
        Year which the output timeseries should end (inclusive)
    """
    res = []
    data = scmdata.ScmRun(data.timeseries().dropna(how="all").dropna(how="all", axis=1))
    ts = data.timeseries()

    def _extend(df: pd.DataFrame) -> scmdata.ScmRun:
        clean_run = scmdata.ScmRun(df.dropna(how="all").dropna(how="all", axis=1))
        assert len(clean_run) == 1  # noqa: S101

        for extension in extensions:
            clean_run = _apply_extension(extension, clean_run)

        # Finally use default extrapolation
        return clean_run.interpolate(
            np.arange(str(start_year), str(end_year + 1), dtype="datetime64[Y]"),
            extrapolation_type=method,
        )

    for i in range(len(data)):
        res.append(_extend(ts.iloc[[i]]))

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
