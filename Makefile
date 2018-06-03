.PHONY: help tests coverage venv venv_dev

VENV_PATH=.venv
VENV_ACTIVATE=. $(VENV_PATH)/bin/activate

.DEFAULT: help

help:
	@echo "Usage:"
	@echo "    make tests           # Run unit tests"
	@echo "    make coverage        # Run unit tests with code coverage measurement"
	@echo "    make integration     # Run integration tests"

venv: setup.py
	(test -d $(VENV_PATH)|| python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U .

venv_dev: setup.py
	(test -d $(VENV_PATH)|| python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U -e .[dev]

coverage: venv_dev
	$(VENV_ACTIVATE) && \
	    pip freeze && \
	    coverage run --branch --source vectty -m unittest -v && coverage report && coverage html

tests: venv
	$(VENV_ACTIVATE) && \
	    pip freeze && \
	    python -m unittest -v

integration: coverage
