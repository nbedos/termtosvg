.PHONY: usage tests venv_dev xresources build deploy_test deploy_prod examples

VENV_PATH=.venv
VENV_ACTIVATE=. $(VENV_PATH)/bin/activate
EXAMPLES_DIR=examples
CASTS_DIR=$(EXAMPLES_DIR)/casts

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make build           # Build source distribution archives"
	@echo "    make deploy_prod     # Upload source distribution archives to pypi.org"
	@echo "    make deploy_test     # Upload source distribution archives to test.pypi.org"
	@echo "    make examples        # Render example SVG animations"
	@echo "    make tests           # Run unit tests"
	@echo "    make xresources      # Update Xresources data from the base16-xresources repository"

build: tests
	$(VENV_ACTIVATE) && \
	    rm -rf dist && \
	    python setup.py sdist bdist_wheel

deploy_test: build
	$(VENV_ACTIVATE) && \
	    twine upload -r pypitest dist/*

deploy_prod: build
	$(VENV_ACTIVATE) && \
	    twine upload -r pypi dist/*

tests: venv_dev
	$(VENV_ACTIVATE) && \
	    pip freeze && \
	    coverage run --branch --source termtosvg -m unittest -v && \
	    coverage report && \
	    coverage html

venv_dev: setup.py
	(test -d $(VENV_PATH) || python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U -e .[dev]

xresources:
	./termtosvg/data/Xresources/update.sh

examples:
	$(VENV_ACTIVATE) && \
	    for cast_file in $$(find $(CASTS_DIR) -name '*.cast'); do \
	    	svg_file="$(EXAMPLES_DIR)/$$(basename --suffix=.cast $$cast_file).svg" && \
		termtosvg render "$$cast_file" "$$svg_file"; \
	    done

