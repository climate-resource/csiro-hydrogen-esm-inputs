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

Not all data required to complete the pipeline can be included in the Git repository
