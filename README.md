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
poetry run doit run <doit-run-args> generate_notebook_tasks --run-id myrun <tasks-to-run>
# For example
poetry run doit run --verbosity 2 -n 4 generate_notebook_tasks --run-id myrun  display_info "Create input4MIPs checklist file"
```

Running in this way allows pydoit's task checking to only re-run tasks where the dependencies have been updated.


### Required data

Not all data required to complete the pipeline can be included in the Git repository.

Before starting you need to create a user-specific placeholder file. This file will contain
so user-specific paths. A sample file is provided at `data/configuration/user.sample.yaml`. The
default location for this file is `data/configuration/user.yaml`, but this can be
modified by passing adding a `--user_placeholders my/custom/user/file.yaml` argument when
running `doit`.

For the gridding step, a range of proxies and seasonality data are needed. These
can be obtained by downloading the results from
[Feng et al. 2020](https://zenodo.org/record/2538194) (this can take
some time so start with that).

Once the outputs from `Feng et al. 2020` have been downloaded, extract them to
`data/raw/emissions_downscaling_archive`. There is a file that appears to be
missing from the archive, it is
`data/raw/emissions_downscaling_archive/gridding/gridding-mappings/country_location_index_05.csv`.
This can be downloaded from
[here](https://github.com/iiasa/emissions_downscaling/blob/master/input/gridding/gridding-mappings/country_location_index_05.csv).
Make sure you have downloaded and saved this file in
`data/raw/emissions_downscaling_archive/gridding/gridding-mappings/country_location_index_05.csv`
before preceeding.

While the Feng data is downloading, install `R` so that
`Rscript` is available on your `PATH`. This step is OS specific, but for MacOS
we recommend using `brew` ([see homebrew](https://brew.sh/)).

If successful, you should be able to run the following and get output like the following

```bash
$ Rscript --version
Rscript (R) version 4.3.0 (2023-04-21)
```

The `aneris` repository with the feng gridding module then needs to be cloned.
Put the `aneris` folder wherever best suits, we recommend putting it in a
folder in the root level of this repository as it is automatically ignored by
our `.gitignore` file.

```bash
git clone git@github.com:lewisjared/aneris.git
cd aneris
git checkout feng
```

You will also need to download MAGICC7 and the AR6 probabilistic file from
https://magicc.org/download/magicc7. The paths to the downloaded files can
then be set in the common configuration under the `magicc_runs` key.
