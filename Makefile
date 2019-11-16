.PHONY: usage tests build deploy_test deploy_prod html man install

PIP=pip
PYTHON=python

EXAMPLES_DIR=docs/examples
CASTS_DIR=$(EXAMPLES_DIR)/casts

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make build           # Build source distribution archives"
	@echo "    make deploy_prod     # Upload source distribution archives to pypi.org"
	@echo "    make deploy_test     # Upload source distribution archives to test.pypi.org"
	@echo "    make man             # Build manual pages"
	@echo "    make html            # Build GitHub pages website"
	@echo "    make tests           # Run unit tests"

install:
	$(PYTHON) --version
	$(PIP) install -U -e .[dev]
	$(PIP) freeze

tests:
	coverage run --branch --source termtosvg -m unittest termtosvg.tests.suite -v
	coverage report
	pylint -j 0 --extension-pkg-whitelist lxml termtosvg/*.py || exit 0

build:
	rm -rf dist && \
	$(PYTHON) setup.py sdist bdist_wheel

man:
	pandoc man/termtosvg.md -s -t man > man/termtosvg.man.1
	pandoc man/termtosvg-templates.md -s -t man > man/termtosvg-templates.man.5
	tar -czf "man_$${TRAVIS_TAG}.tar.gz" man/termtosvg*.man.*

html:
	cp -r termtosvg/data/templates/ docs/
	termtosvg render $(CASTS_DIR)/awesome.cast $(EXAMPLES_DIR)/awesome_window_frame_powershell.svg -t window_frame_powershell
	termtosvg render $(CASTS_DIR)/awesome.cast $(EXAMPLES_DIR)/awesome_window_frame_js.svg -t window_frame_js
	termtosvg render $(CASTS_DIR)/colors.cast $(EXAMPLES_DIR)/colors_progress_bar.svg -t progress_bar
	termtosvg render $(CASTS_DIR)/htop.cast $(EXAMPLES_DIR)/htop_gjm8.svg -t gjm8
	termtosvg render $(CASTS_DIR)/ipython.cast $(EXAMPLES_DIR)/ipython_window_frame.svg -t window_frame
	termtosvg render $(CASTS_DIR)/unittest.cast $(EXAMPLES_DIR)/unittest_solarized_dark.svg -t solarized_dark
	for template in $$(ls termtosvg/data/templates/*.svg | grep -v gjm8_play); \
	    do \
	    	filename="$$(basename $$template)"; \
		termtosvg render "$(CASTS_DIR)/awesome.cast" "$(EXAMPLES_DIR)/$$filename" -t "$$template"; \
	    done

deploy_test:
	twine upload -r pypitest dist/*

deploy_prod:
	twine upload -r pypi dist/*

