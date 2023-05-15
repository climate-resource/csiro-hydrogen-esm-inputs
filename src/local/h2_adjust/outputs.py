"""
input4MIPs dataset generation
"""
import logging
import os
import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

import numpy as np
import xarray as xr
from attrs import asdict, define, field
from typing_extensions import Self

logger = logging.getLogger(__name__)

required_attributes = [
    "Conventions",
    "activity_id",
    "contact",
    "creation_date",
    "dataset_category",
    "frequency",
    "further_info_url",
    "grid_label",
    "institution",
    "institution_id",
    "mip_era",
    "nominal_resolution",
    "realm",
    "source",
    "source_id",
    "source_version",
    "target_mip",
    "title",
    "tracking_id",
    "variable_id",
]
optional_attributes = [
    "comment",
    "data_specs_version",
    "external_variables",
    "grid",
    "history",
    "license",
    "product",
    "references",
    "region",
    "release_year",
    "source_type",
    "table_id",
    "table_info",
]


@define
class Input4MIPsMetadata:
    """
    Possible metadata in an Input4MIPs dataset
    """

    contact: str
    creation_date: str = field(init=False)
    dataset_category: str
    frequency: str
    further_info_url: str
    grid_label: str
    institution: str
    institution_id: str
    nominal_resolution: str
    realm: str
    source: str
    source_id: str
    source_version: str
    target_mip: str
    title: str
    variable_id: str
    Conventions: str = "CF-1.7 CMIP-6.2"
    activity_id: str = "input4MIPs"
    mip_era: str = "CMIP6"

    def __attrs_post_init__(self):
        """
        Update the creation date
        """
        self.creation_date = datetime.utcnow().isoformat()


def _generate_hdl() -> str:
    return "hdl:21.14100/" + str(uuid.uuid4())


def _generate_bounds(points, bound_position=0.5):
    diffs = np.diff(points)
    diffs = np.insert(diffs, 0, diffs[0])
    diffs = np.append(diffs, diffs[-1])

    min_bounds = points - diffs[:-1] * bound_position
    max_bounds = points + diffs[1:] * (1 - bound_position)

    return np.array([min_bounds, max_bounds]).transpose()


class Input4MIPsDataset:
    """
    A single Input4MIPs file
    """

    #
    directory_template = "{activity_id}/{mip_era}/{target_mip}/{institution_id}/{source_id}/{realm}/{frequency}/{variable_id}/{grid_label}/{version}"  # noqa
    filename_template = "{variable_id}_{activity_id}_{dataset_category}_{target_mip}_{source_id}_{grid_label}_{start_date}-{end_date}.nc"  # noqa
    dimensions: tuple[str, ...] = ("time", "lat", "lon")

    root_data_dir = "."

    def __init__(self, data: xr.Dataset, metadata: Input4MIPsMetadata, version: str):
        self.data = data
        self.metadata = metadata
        self.version = version

        self.prepare()

    def prepare(self) -> xr.Dataset:
        """
        Quick checks to verify that data is formatted as expected

        Returns
        -------
            Dataset ready for data
        """
        assert self.metadata.variable_id in self.data  # noqa: S101
        assert (  # noqa: S101
            self.data[self.metadata.variable_id].dims == self.dimensions
        )

        for variable in self.dimensions:
            self._add_bounds(variable)

        ds_metadata = asdict(self.metadata)
        self.data.attrs.update(ds_metadata)

        self._update_lat()
        self._update_lon()
        self._update_time()

        return self.data

    def _get_filename(self, **extra_kwargs):
        avail_metadata = {
            "version": self.version,
            **asdict(self.metadata),
            **extra_kwargs,
        }
        for k in avail_metadata:
            avail_metadata[k] = avail_metadata[k].replace("_", "-")
        out_dir = self.directory_template.format(**avail_metadata)
        out_fname = self.filename_template.format(**avail_metadata)

        return os.path.join(self.root_data_dir, out_dir, out_fname)

    def write_slice(self, ds: xr.Dataset) -> None:
        """
        Write a slice of data to the dataset

        Parameters
        ----------
        ds
            Data to write
        """
        # TODO check if end conditions
        out_fname = self._get_filename(
            start_date=ds.time.to_numpy().min().strftime("%Y%m"),
            end_date=ds.time.to_numpy().max().strftime("%Y%m"),
        )

        # Tracking id is unique for each file
        ds.attrs["tracking_id"] = _generate_hdl()

        os.makedirs(os.path.dirname(out_fname), exist_ok=True)
        ds.to_netcdf(
            out_fname,
            unlimited_dims=("time",),
            encoding={self.metadata.variable_id: {"zlib": True, "complevel": 5}},
        )

    def _update_lon(self):
        metadata = {
            "units": "degrees_east",
            "long_name": "longitude",
            "axis": "X",
            "modulo": "360",
            "standard_name": "longitude",
            "topology": "circular",
        }
        self.data.lon.attrs.update(metadata)

    def _update_lat(self):
        metadata = {
            "units": "degrees_north",
            "long_name": "latitude",
            "axis": "Y",
            "standard_name": "latitude",
            "topology": "linear",
        }
        self.data.lat.attrs.update(metadata)

    def _update_time(self):
        metadata = {
            "long_name": "time",
            "axis": "T",
            "standard_name": "time",
        }
        self.data.time.attrs.update(metadata)

    def _add_bounds(self, variable, suffix="_bounds"):
        """Add bounds to a variable"""
        exp_variable = variable + suffix

        if exp_variable in self.data:
            return

        bounds = xr.DataArray(
            _generate_bounds(self.data[variable]), dims=(variable, "bounds")
        )

        self.data[exp_variable] = bounds


class GriddedEmissionsDataset(Input4MIPsDataset):
    """
    Gridded emissions dataset
    """

    dimensions = ("time", "sector", "lat", "lon")

    @classmethod
    def create_empty(  # noqa: PLR0913
        cls,
        sectors: Sequence[str],
        time: Sequence[Any],
        lat: Sequence[float],
        lon: Sequence[float],
        version: str,
        metadata: Input4MIPsMetadata,
    ) -> Self:
        """
        Create an empty dataset

        Parameters
        ----------
        sectors
            Sectors present
        time
            Time values
        lat
            Latitude values
        lon
            Longitude values
        version

        metadata
            Metadata configuration to use

        Returns
        -------
            A prepared dataset with the appropriate dimensions
        """
        sector_dimension = xr.IndexVariable(
            "sector",
            range(len(sectors)),
            attrs={
                "long_name": "sector",
                "ids": "; ".join([f"{v}: {name}" for v, name in enumerate(sectors)]),
            },
        )
        da = xr.DataArray(
            data=np.zeros((len(time), len(sectors), len(lat), len(lon))),
            coords=(time, sector_dimension, lat, lon),  # type: ignore
        )
        da[:] = np.nan
        da.name = metadata.variable_id

        return cls(da.to_dataset(), metadata, version)


class GriddedAircraftEmissionsDataset(Input4MIPsDataset):
    """
    Gridded Aircraft emissions dataset
    """

    dimensions = ("time", "level", "lat", "lon")

    @classmethod
    def create_empty(  # noqa: PLR0913
        cls,
        levels: Iterable[float],
        time: Sequence[Any],
        lat: Sequence[float],
        lon: Sequence[float],
        version: str,
        metadata: Input4MIPsMetadata,
    ) -> Self:
        """
        Create an empty file

        Parameters
        ----------
        levels
            Vertical levels present
        time
            Time values
        lat
            Latitude values
        lon
            Longitude values
        version

        metadata
            Metadata configuration to use

        Returns
        -------
            A prepared dataset with the appropriate dimensions
        """
        level_dimension = xr.IndexVariable(
            "level",
            levels,
            attrs={"long_name": "altitude", "units": "km"},
        )
        da = xr.DataArray(
            data=np.zeros((len(time), len(level_dimension), len(lat), len(lon))),
            coords=(time, level_dimension, lat, lon),  # type: ignore
        )
        da[:] = np.nan
        da.name = metadata.variable_id

        return cls(da.to_dataset(), metadata, version)
