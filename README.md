# CSIRO Hydrogen ESM Inputs

[TODO badges etc.]

Generation of hydrogen and associated input files for CSIRO's earth system
modelling. This work was performed as part of the [TODO funding etc. stuff
here].

## Installation

We rely on `poetry <https://python-poetry.org>`_ for all our dependency
management. To get started, you will need to make sure that poetry is installed
(https://python-poetry.org/docs/#installing-with-the-official-installer, we
found that pipx and pip worked better to install on a Mac).

For all of work, we use our `Makefile`.
You can read the instructions out and run the commands by hand if you wish,
but we generally discourage this because it can be error prone and doesn't
update if dependencies change (e.g. the environment is updated).
In order to create your environment, run `make virtual-environment`.

If there are any issues, the messages from the `Makefile` should guide you
through. If not, please raise an issue in the
[issue tracker](https://gitlab.com/climate-resource/csiro/csiro-hydrogen-esm-inputs/-/issues).

## Run

To create all the outputs, we use [pydoit](https://pydoit.org/install.html).
To run everything, simply run `make all`.

If you want to have more control, you can specify the output run ID with the
below

```sh
poetry run doit run --verbosity 2 display_info crunch_scenarios --run-id myrun
```

Running in this way allows pydoit's task checking to only re-run tasks where the dependencies have been updated.


### Required data

Not all data required to complete the pipeline can be included in the Git repository.

For the gridding step, a range of proxies and seasonality data are needed. These
can be obtained by downloading the results from
[Feng et al. 2020](https://zenodo.org/record/2538194) (this can take
some time so start with that). While that is downloading, install `R` so that
`Rscript` is available on your `PATH`. This step is OS specific, but for MacOS
we recommend using `brew`.

The `aneris` repository with the feng gridding module then needs to be cloned and setup.
In this case we are creating a local virtual environment instead of having to setup
`aneris`'s complete conda development environment.

```bash
git clone git@github.com:lewisjared/aneris.git
cd aneris
git checkout feng
python -m venv venv
source venv/bin/activate
pip install pyreadr xarray pandas numpy joblib
```

Once `aneris` and the outputs from `Feng et al. 2020` have been downloaded and extracted to
`data/raw/emissions_downscaling_archive` inside the aneris repository, the processing
notebook can be run.

The `notebooks/gridding/010_prepare_input_data.py` notebook preprocesses the
required data from `Feng et al` into a set of data that can be easily read
by Python.

The results of this preprocessing should be available in `data/processed/gridding`.
This directory is the `historical_h2_gridding.grid_data_directory` configuration
variable (TODO: figure out how to make this non-user-specific) and contains the
following subdirectories:

```bash
data/processed
└── gridding
    ├── masks
    ├── proxies
    ├── seasonality
    └── seasonality-temp
```
