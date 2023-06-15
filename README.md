#

<!---
Can use start-after and end-before directives in docs, see
https://myst-parser.readthedocs.io/en/latest/syntax/organising_content.html#inserting-other-documents-directly-into-the-current-document
-->

<!--- sec-begin-description -->




# TODO: get something that gets the project org and repo from the url so it can be used here
**Repository health :**
[![CI](https://github.com/climate-resource/csiro-hydrogen-esm-inputs/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/climate-resource/csiro-hydrogen-esm-inputs/actions/workflows/ci.yaml)
[![Coverage](https://codecov.io/gh/climate-resource/csiro-export/branch/main/graph/badge.svg)](https://codecov.io/gh/climate-resource/csiro-export)
[![Docs](https://readthedocs.org/projects/csiro-export/badge/?version=latest)](https://csiro-export.readthedocs.io)

**PyPI :**
[![PyPI](https://img.shields.io/pypi/v/csiro-export.svg)](https://pypi.org/project/csiro-export/)
[![PyPI: Supported Python versions](https://img.shields.io/pypi/pyversions/csiro-export.svg)](https://pypi.org/project/csiro-export/)
[![PyPI install](https://github.com/climate-resource/csiro-hydrogen-esm-inputs/actions/workflows/install.yaml/badge.svg?branch=main)](https://github.com/climate-resource/csiro-hydrogen-esm-inputs/actions/workflows/install.yaml)

**Other info :**
[![License](https://img.shields.io/github/license/climate-resource/csiro-export.svg)](/blob/main/LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/climate-resource/csiro-export.svg)](/commits/main)
[![Contributors](https://img.shields.io/github/contributors/climate-resource/csiro-export.svg)](/graphs/contributors)


<!--- sec-end-description -->

Full documentation can be found at:
[csiro-export.readthedocs.io](https://csiro-export.readthedocs.io/en/latest/).
We recommend reading the docs there because the internal documentation links
don't render correctly on GitHub's viewer.

## Installation

<!--- sec-begin-installation -->

 can be installed with conda or pip:

```bash
pip install csiro-export
conda install -c conda-forge csiro-export
```


<!--- sec-end-installation -->

### For developers

<!--- sec-begin-installation-dev -->

For development, we rely on [poetry](https://python-poetry.org) for all our
dependency management. To get started, you will need to make sure that poetry
is installed
([instructions here](https://python-poetry.org/docs/#installing-with-the-official-installer),
we found that pipx and pip worked better to install on a Mac).

For all of work, we use our `Makefile`.
You can read the instructions out and run the commands by hand if you wish,
but we generally discourage this because it can be error prone.
In order to create your environment, run `make virtual-environment`.

If there are any issues, the messages from the `Makefile` should guide you
through. If not, please raise an issue in the [issue tracker][issue_tracker].

For the rest of our developer docs, please see [](development-reference).

[issue_tracker]: https://github.com/climate-resource/csiro-hydrogen-esm-inputs/issues

<!--- sec-end-installation-dev -->
