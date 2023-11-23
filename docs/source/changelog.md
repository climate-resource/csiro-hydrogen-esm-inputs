# Changelog

Versions follow [Semantic Versioning](https://semver.org/) (`<major>.<minor>.<patch>`).

Backward incompatible (breaking) changes will only be introduced in major versions
with advance notice in the **Deprecations** section of releases.


<!--
You should *NOT* be adding new changelog entries to this file, this
file is managed by towncrier. See changelog/README.md.

You *may* edit previous changelogs to fix problems like typo corrections or such.
To add a new changelog entry, please see
https://pip.pypa.io/en/latest/development/contributing/#news-entries,
noting that we use the `changelog` directory instead of news, md instead
of rst and use slightly different categories.
-->

<!-- towncrier release notes start -->


## v0.5.0 (2023-06-06)

### Feat

- Remove photochemical production baseline emissions
- Increase production leakages rates to cover all fuels

## v0.4.2 (2023-06-02)

### Fix

- Remove static config_file

## v0.4.1 (2023-06-02)

### Fix

- resolve double counting in final figures

## v0.4.0 (2023-06-02)

### Feat

- Use specific sectors from CEDS when calculating baseline H2 emissions

## v0.3.0 (2023-05-30)

### Fix

- Updates from preliminary run-through

## v0.2.1 (2023-05-28)

### Fix

- Include dependency for h2 data in spaemis tasks

## v0.2.0 (2023-05-28)

### BREAKING CHANGE

- Run interface and some other internal interfaces (e.g. `NotebookStep`) have now changed.
- Removed `mod`:local.pydoit in favour of :mod:`local.pydoit_nb`

### Feat

- **zenodo**: add upload to zenodo
- Enable production settings
- **emissions**: Add the calculation of additional production emissions in Australia
- **configuration**: Add additional SSPs
- **preparation**: Adds extra notebooks for generating the grids required for aneris
- **configuration**: Support running multiple scenarios with shared historical tasks
- **configuration**: Refactor merging strategy into a function
- **concentrations**: Use the calculated emissions file instead of the test file
- **configuration**: Added medium and high variants for ssp119
- **configuration**: Add support for multiple scenarios
- **spaemis**: Add support for multiple spatial emissions setups
- **spaemis**: Add spaemis notebook for calculating regional emissions
- add concentration gridding notebooks
- **h2-historical**: Add gridding
- **h2-historical**: Add country downscaling
- **h2-historical**: Added first notebook
- **configuration**: Adds configuration option to a NotebookStep
- get basic doit task running

### Fix

- **pipeline**: Sync versions between concentrations and emissions
- **configuration**: Add user specific placeholder values
- **configuration**: Fix pickling of Frozen dict
- fix up task creation to allow better control of run parameters
- Use checklists to track directory contents

### Refactor

- clean up to decouple creation assumptions from run assumptions
