.PHONY: usage tests venv_dev build deploy_test deploy_prod static man


VENV_PATH=.venv
VENV_ACTIVATE=. $(VENV_PATH)/bin/activate
EXAMPLES_DIR=examples
CASTS_DIR=$(EXAMPLES_DIR)/casts
TEMPLATES_DIR=termtosvg/data/templates

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make build           # Build source distribution archives"
	@echo "    make deploy_prod     # Upload source distribution archives to pypi.org"
	@echo "    make deploy_test     # Upload source distribution archives to test.pypi.org"
	@echo "    make man             # Build manual pages"
	@echo "    make static          # Render examples of SVG animations"
	@echo "    make tests           # Run unit tests"

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
	    coverage report --omit 'termtosvg/tests/*' && \
	    coverage html
	-$(VENV_ACTIVATE) && \
	    pylint -j 0 --extension-pkg-whitelist lxml termtosvg/*.py

venv_dev: setup.py
	(test -d $(VENV_PATH) || python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install -U -e .[dev]

man: venv_dev
	$(VENV_ACTIVATE) && \
	    pandoc man/termtosvg.md -s -t man > man/termtosvg.man.1 && \
	    pandoc man/termtosvg-templates.md -s -t man > man/termtosvg-templates.man.5

static: man
	(test -d $(VENV_PATH) || python -m venv $(VENV_PATH))
	$(VENV_ACTIVATE) && \
	    pip install . -U && \
	    rm -rf examples/*.svg && \
	    termtosvg render $(CASTS_DIR)/awesome.cast $(EXAMPLES_DIR)/awesome_window_frame.svg -t window_frame && \
	    termtosvg render $(CASTS_DIR)/awesome.cast $(EXAMPLES_DIR)/awesome_window_frame_js.svg -t window_frame_js && \
	    termtosvg render $(CASTS_DIR)/colors.cast $(EXAMPLES_DIR)/colors_progress_bar.svg -t progress_bar && \
	    termtosvg render $(CASTS_DIR)/htop.cast $(EXAMPLES_DIR)/htop_gjm8.svg -t gjm8 && \
	    termtosvg render $(CASTS_DIR)/ipython.cast $(EXAMPLES_DIR)/ipython_window_frame.svg -t window_frame && \
	    termtosvg render $(CASTS_DIR)/unittest.cast $(EXAMPLES_DIR)/unittest_solarized_dark.svg -t solarized_dark
	    rm -rf docs/examples/ && mkdir docs/examples && cp examples/*.svg docs/examples/
	    rm -rf docs/templates/ && cp -r termtosvg/data/templates docs/

