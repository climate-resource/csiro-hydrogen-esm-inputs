# Makefile to help automate key steps

.DEFAULT_GOAL := help
TEMP_FILE := $(shell mktemp)

# A helper script to get short descriptions of each target in the Makefile
define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([\$$\(\)a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-30s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT


help:  ## print short description of each target
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

all:  ## compile all the outputs
	poetry run doit run

.PHONY: checks
checks:  ## run all the linting checks of the codebase
	@echo "=== pre-commit ==="; poetry run pre-commit run --all-files || echo "--- pre-commit failed ---" >&2; \
		echo "=== mypy ==="; MYPYPATH=stubs poetry run mypy src notebooks || echo "--- mypy failed ---" >&2; \
		echo "======"

.PHONY: black
black:  ## format the code using black
	poetry run black dodo.py src notebooks scripts
	poetry run blackdoc src

.PHONY: ruff-fixes
ruff-fixes:  ## fix the code using ruff
	poetry run ruff dodo.py src notebooks --fix

.PHONY: check-commit-messages
check-commit-messages:  ## check commit messages
        # If you only want to check a certain range (e.g. we
        # have old commits we don't want to re-write), this
        # can be changed to
        # poetry run cz check --rev-range <commit-to-start-from-sha>..HEAD
	poetry run cz check --rev-range 62b58b90..HEAD

.PHONY: licence-check
licence-check:  ## Check that licences of the dependencies are suitable
	# Not sure if this is cross-platform compatible
	poetry export --without=tests --without=docs --without=dev > $(TEMP_FILE)
	poetry run liccheck -r $(TEMP_FILE) -R licence-check.txt
	rm -f $(TEMP_FILE)

.PHONY: virtual-environment
virtual-environment:  ## update virtual environment, create a new one if it doesn't already exist
	poetry lock
	# Put virtual environments in the project
	poetry config virtualenvs.in-project true
	poetry install --all-extras
	poetry run pre-commit install
