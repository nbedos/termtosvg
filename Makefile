.PHONY: usage tests venv_dev xresources build deploy_test deploy_prod

VENV_PATH=.venv
VENV_ACTIVATE=. $(VENV_PATH)/bin/activate

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make build           # Build source distribution archives"
	@echo "    make deploy_prod     # Upload source distribution archives to pypi.org"
	@echo "    make deploy_test     # Upload source distribution archives to test.pypi.org"
	@echo "    make tests           # Run unit tests"
	@echo "    make xresources      # Update Xresources data from the base16-xresources repository"

build: tests
	$(VENV_ACTIVATE) && \
	    python setup.py sdist bdist_wheel

deploy_test: build
	$(VENV_ACTIVATE) && \
	    twine upload --repository-url https://test.pypi.org/legacy/ dist/*

deploy_prod: build
	$(VENV_ACTIVATE) && \
	    twine upload --repository-url http://pypi.python.org/pypi/ dist/*

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
