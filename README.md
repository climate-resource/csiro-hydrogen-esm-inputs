# CSIRO Hydrogen ESM Inputs

[TODO badges etc.]

Generation of hydrogen and associated input files for CSIRO's earth system
modelling. This work was performed as part of the [TODO funding etc. stuff
here].

This is an "application" repository which contains the set of notebooks and
configuration to be able to reproduce the outputs from this study. The more
generic parts of the methodology are contained in other python libraries so
they can be reused by a range of other projects. This project contains a
tree of notebooks in that are the glue that combines the project-specific
choices with the building blocks from these external libraries.

As part of this project, two new libraries were developed:

* [spaemis](https://spaemis.readthedocs.com/) - Spatial emissions scaling
* [carpet-concentration](https://github.com/climate-resource/carpet-concentrations)
    - GHG concentration input file generation

There were a range of project-specific choices that were made such as emissions
intensities, scaling proxies. As more information comes available, these assumptions
can be modified to generate an updated dataset.

## Installation

This repository should be cloned from the [GitHub repository](https://github.com/climate-resource/csiro-hydrogen-esm-inputs).
Since this is an application repository, the package isn't installable via pypi or
conda.

```bash
git clone https://github.com/climate-resource/csiro-hydrogen-esm-inputs.git
```

We rely on `poetry <https://python-poetry.org>`_ for all our dependency
management. To get started, you will need to make sure that poetry is installed
(https://python-poetry.org/docs/#installing-with-the-official-installer, we
found that pipx and pip worked better to install on a Mac). Poetry creates a lock file
(`poetry.lock`) which contains the versions of any dependencies used by this project
to ensure someone else can generate the exact same python environment.

There is one private repository that is required to reproduce the results for this project.
This [dependency will eventually be removed](https://github.com/climate-resource/csiro/csiro-hydrogen-esm-inputs/-/issues/16)
to make the project easier to install.[Jared Lewis](mailto:jared.lewis@climate-resource.com)
can provide access to this repository if requested. Poetry requires some additional
configuration before the project dependencies can be installed.

```
poetry config repositories.git-lewisjarednz-domestic_pathways https://gitlab.com/lewisjarednz/domestic_pathways.git
poetry config http-basic.git-lewisjarednz-domestic_pathways <gitlab-username> <gitlab-password>
```

The project dependencies can then be installed. Poetry will create a local virtual
environment (`.venv`) to isolate this environment from other projects.

```bash
make virtual-environment
```

We use a `Makefile` to run common processing steps.
You can read the instructions out and run the commands by hand if you wish,
but we generally discourage this because it can be error-prone and doesn't
update if dependencies change (e.g. the environment is updated).

If there are any issues, the messages from the `Makefile` should guide you
through. If not, please raise an issue in the
[issue tracker](https://github.com/climate-resource/csiro-hydrogen-esm-inputs/-/issues).

## Architecture

A large configuration class is used to manage the required configuration for
a given scenario.

There are some common configuration and user-specific configuration that is
merged with the configuration for each scenario. The common configuration and
user-specific configuration is located at `data/configuration/common.yaml` and
`data/configuration/user.yaml` respectively.

With a given configuration, the steps that are required to generate the results
can be created (`src/local/steps.py`). Each step consists of:

* A notebook to be run
* A set of input files that are required by the notebook
* A set of files that will be produced by the notebook (figures, data, diagnostics)
* The configuration values that are required by the notebook

`pydoit` uses these steps to build a graph of what work needs to be performed to
complete all the steps. If any part of the step has been modified that step (and
all steps that depend on that step) will be rerun. Some of the steps are duplicated
for each scenario and will only be run once, for example the generation of
historical gridded H2 fields.


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

To generate the regional emissions two additional datasets are required:

* The Australia and Victoria emissions inventories
* input4MIPs emissions data for `IAMC-IMAGE-ssp119-1-1`, `IAMC-IMAGE-ssp126-1-1`
  and `IAMC-REMIND-MAGPIE-ssp245-1-1`

Additional information about the required input4MIPs dataset is provided at
the [spaemis input data documentation](https://spaemis.readthedocs.io/en/latest/input_data.html).
The spaemis repository also contains the required inventory data.
The user-specific placeholders contain placeholders for the required paths.

## Run

Once the virtual environment has been created, the required input data have been obtained
and the user-specific placeholders created, the system is ready to run.

To run everything, simply run `make all`.

If you want to have more control, you can specify the output run ID with the
below

```sh
poetry run doit run <doit-run-args> generate_notebook_tasks --run-id myrun <tasks-to-run>
# For example
poetry run doit run --verbosity 2 -n 4 generate_notebook_tasks --run-id myrun  display_info "Create input4MIPs checklist file"
```

Running in this way allows pydoit's task checking to only re-run tasks where the dependencies have been updated.
