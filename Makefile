.PHONY: help tests coverage

VENV_NAME?=.venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python3

.DEFAULT: help
help:
	@echo "make coverage|tests"

venv: setup.py
	test -d $(VENV_PATH) || ${PYTHON} -m venv $(VENV_PATH)
	${PYTHON} -m pip install -U .

coverage:
	coverage run --branch --source vectty -m unittest && coverage html

tests:
	${PYTHON} -m unittest
