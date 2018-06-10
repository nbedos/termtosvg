.PHONY: usage tests venv_dev xresources

VENV_PATH=.venv
VENV_ACTIVATE=. $(VENV_PATH)/bin/activate

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make tests           # Run unit tests"
	@echo "    make xresources      # Update Xresources data from the base16-xresources repository"

venv_dev: setup.py
	(test -d $(VENV_PATH) || python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U -e .[dev]

tests: venv_dev
	$(VENV_ACTIVATE) && \
	    pip freeze && \
	    coverage run --branch --source termtosvg -m unittest -v && \
	    coverage report && \
	    coverage html

xresources:
	./termtosvg/data/Xresources/update.sh
