.PHONY: usage tests coverage venv venv_dev xresources

VENV_PATH=.venv
VENV_ACTIVATE=. $(VENV_PATH)/bin/activate

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make coverage        # Run unit tests with code coverage measurement"
	@echo "    make integration     # Run integration tests"
	@echo "    make tests           # Run unit tests"
	@echo "    make xresources      # Update Xresources data from the base16-xresources repository"

venv: setup.py
	(test -d $(VENV_PATH) || python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U .

venv_dev: setup.py
	(test -d $(VENV_PATH) || python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U -e .[dev]

coverage: venv_dev
	$(VENV_ACTIVATE) && \
	    pip freeze && \
	    coverage run --branch --source termtosvg -m unittest -v && \
	    coverage report && \
	    coverage html

tests: venv
	$(VENV_ACTIVATE) && \
	    pip freeze && \
	    python -m unittest -v

integration: coverage

xresources:
	./termtosvg/data/Xresources/update.sh
