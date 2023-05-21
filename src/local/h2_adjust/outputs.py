"""
input4MIPs dataset generation
"""
import logging
import os
import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

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

SECTOR_MAP = [
    "Agriculture",
    "Energy Sector",
    "Industrial Sector",
    "Transportation Sector",
    "Residential, Commercial, Other",
    "Solvents production and application",
    "Waste",
    "International Shipping",
    # "Negative CO2 Emissions", # CO2 also includes this additional sector, but we aren't regridding that here
]
LEVELS = [
    0.305,
    0.915,
    1.525,
    2.135,
    2.745,
    3.355,
    3.965,
    4.575,
    5.185,
    5.795,
    6.405,
    7.015,
    7.625,
    8.235,
    8.845,
    9.455,
    10.065,
    10.675,
    11.285,
    11.895,
    12.505,
    13.115,
    13.725,
    14.335,
    14.945,
]


def _load_slice(filename: str | Path) -> xr.DataArray:
    da = xr.load_dataarray(filename)

    # input4MIPs flipped the lat axis compared to the proxies
    da = da.reindex(lat=list(reversed(da.lat)))
    assert da.lat[0] < da.lat[-1]  # noqa
    return da


def find_gridded_slice(
    variable: str, sector: str, slice_years: str, gridded_data_directory: Path
) -> xr.DataArray | None:
    """
    Get a single slice of gridded data

    Parameters
    ----------
    variable
        Variable name
    sector
        Sector
    slice_years
        Filter for the years that a dataset covers

    gridded_data_directory
        Directory containing the preprocessed gridded files

    Returns
    -------
        If found the loaded slice
    """
    matches = list(
        gridded_data_directory.rglob(f"Emissions_{variable}_{sector}*_{slice_years}.nc")
    )

    if len(matches) > 1:
        raise ValueError(f"More than one match exists: {matches}")  # noqa
    if matches:
        return _load_slice(matches[0])
    logger.info(f"No matching existing file found {variable}/{sector}")

    return None


def check_dims(a: xr.DataArray, b: xr.DataArray, dimensions: Iterable[str]) -> None:
    """
    Check that a subset of dimension of a xarray are consistent

    Parameters
    ----------
    a
        Item A
    b
        Item B
    dimensions
        Dimensions to check
    """
    assert a.shape == b.shape  # noqa

    for d in dimensions:
        xr.testing.assert_allclose(a[d], b[d])


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


class SupportsWriteSlice(Protocol):
    """
    Interface for writing a slice of data in the input4MIPs form
    """

    def __call__(  # noqa: PLR0913, D102
        self,
        example_da: xr.DataArray,
        output_variable: str,
        version: str,
        years_slice: str,
        common_meta: dict[str, str],
        root_data_directory: Path,
        gridded_data_directory: Path,
        baseline: xr.Dataset | None = None,
    ) -> None:
        ...


def write_anthropogenic_slice(  # noqa: PLR0913
    example_da: xr.DataArray,
    output_variable: str,
    version: str,
    years_slice: str,
    common_meta: dict[str, str],
    root_data_directory: Path,
    gridded_data_directory: Path,
    baseline: xr.Dataset | None = None,
) -> None:
    """
    Write an anthropogenic emissions dataset in the Input4MIPs style

    Parameters
    ----------
    example_da
    output_variable
        Variable Identifier
    version
        Version identifier for the data release
    years_slice
        Used to differentate between a varable with multiple timeslices

        #TODO: remove the need for this and gridded_data_directory by using
        dependency injection
    common_meta
        Metadata to add to the
    root_data_directory
        Where to write the output data
    gridded_data_directory
        Where the gridded data are located
    baseline
        Existing dataset used to infill any missing sectors
    """
    variable_id = f"{output_variable}_em_anthro"

    ds = GriddedEmissionsDataset.create_empty(
        time=example_da.time,
        lat=example_da.lat,
        lon=example_da.lon,
        sectors=SECTOR_MAP,
        version=version,
        metadata=Input4MIPsMetadata(
            variable_id=variable_id,
            **common_meta,
        ),
    )
    ds.root_data_dir = str(root_data_directory)
    ds.data[variable_id].attrs.update(
        {
            "units": "kg m-2 s-1",
            "cell_methods": "time: mean",
            "long_name": f"{output_variable} Anthropogenic Emissions",
        }
    )

    if baseline is not None:
        logger.info(f"Using baseline for {variable_id}")
        check_dims(
            ds.data[variable_id],
            baseline[variable_id],
            ("lat", "sector", "lon", "time"),
        )
        ds.data[variable_id][:] = baseline[variable_id][:]

    for sector_idx, sector in enumerate(SECTOR_MAP):
        new_data = find_gridded_slice(
            output_variable,
            sector,
            years_slice,
            gridded_data_directory=gridded_data_directory,
        )

        if new_data is not None:
            check_dims(
                ds.data[variable_id].isel(sector=sector_idx).drop(("sector",)),  # type: ignore
                new_data,
                ("lat", "lon", "time"),
            )
            # This will explode if not lined up correctly
            ds.data[variable_id][:, sector_idx] = new_data[:]

    # These sizes come from the input4MIPs data
    ds.data[variable_id].encoding.update(
        {"chunksizes": {"time": 1, "sector": 4, "lat": 180, "lon": 360}}
    )
    ds.write_slice(ds.data)


def write_anthropogenic_AIR_slice(  # noqa: PLR0913
    example_da: xr.DataArray,
    output_variable: str,
    version: str,
    years_slice: str,
    common_meta: dict[str, str],
    root_data_directory: Path,
    gridded_data_directory: Path,
    baseline: xr.Dataset | None = None,
) -> None:
    """
    Write an aircraft anthropogenic emissions dataset in the Input4MIPs style

    Parameters
    ----------
    example_da
    output_variable
        Variable Identifier
    version
        Version identifier for the data release
    years_slice
        Used to differentiate between a variable with multiple timeslices

        #TODO: remove the need for this and gridded_data_directory by using
        dependency injection
    common_meta
        Metadata to add to the
    root_data_directory
        Where to write the output data
    gridded_data_directory
        Where the gridded data are located
    baseline
        Existing dataset used to infill any missing sectors
    """
    variable_id = f"{output_variable}_em_AIR_anthro"

    ds = GriddedAircraftEmissionsDataset.create_empty(
        time=example_da.time,
        lat=example_da.lat,
        lon=example_da.lon,
        levels=LEVELS,
        version=version,
        metadata=Input4MIPsMetadata(
            variable_id=variable_id,
            **common_meta,
        ),
    )
    ds.root_data_dir = str(root_data_directory)
    ds.data[variable_id].attrs.update(
        {
            "units": "kg m-2 s-1",
            "cell_methods": "time: mean",
            "long_name": f"{output_variable} Anthropogenic Emissions",
        }
    )
    del ds.data["level_bounds"]

    if baseline is not None:
        logger.info(f"Using baseline for {variable_id}")
        check_dims(
            ds.data[variable_id], baseline[variable_id], ("level", "lat", "lon", "time")
        )

        # Override the level dimension. There might be floating point errors which cause xr to explode
        baseline["level"] = ds.data.level
        assert ds.data[variable_id].shape == baseline[variable_id].shape  # noqa
        ds.data[variable_id][:] = baseline[variable_id][:]

    updated_data = find_gridded_slice(
        output_variable,
        "Aircraft",
        years_slice,
        gridded_data_directory=gridded_data_directory,
    )
    if updated_data is not None:
        updated_data = updated_data.transpose(*ds.dimensions)
        check_dims(
            ds.data[variable_id],
            updated_data,
            ("level", "lat", "lon", "time"),
        )

        ds.data[variable_id][:] = updated_data[:]
    # These sizes come from the input4MIPs data
    ds.data[variable_id].encoding.update(
        {"chunksizes": {"time": 1, "level": 13, "lat": 180, "lon": 360}}
    )
    ds.write_slice(ds.data)
