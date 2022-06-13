.DEFAULT_GOAL := all
isort = isort picoprobe examples test
black = black --target-version py37 picoprobe examples test

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: lint
lint:
	$(black) --check --diff
	flake8 picoprobe/ examples/ test/
	#pylint picoprobe/ #examples/ test/
	pydocstyle picoprobe/


.PHONY: mypy
mypy:
	mypy --config-file setup.cfg --package picoprobe
	mypy --config-file setup.cfg picoprobe/
	mypy --config-file setup.cfg examples/

.PHONY: all
all: format lint mypy