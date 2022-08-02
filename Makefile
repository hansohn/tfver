MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:

# include makefiles
export SELF ?= $(MAKE)
PROJECT_PATH ?= $(shell 'pwd')
include $(PROJECT_PATH)/Makefile.*

all: build
.PHONY: all

REPO_NAME ?= $(shell basename $(CURDIR))
SRC_DIR := src

#-------------------------------------------------------------------------------
# python
#-------------------------------------------------------------------------------

PYTHON_VERSION ?= 3.9

# -- python venv --
VIRTUALENV_DIR ?= .venv

VENV_CFG := $(VIRTUALENV_DIR)/pyvenv.cfg
$(VENV_CFG):
	@echo "[INFO] Creating python virtual env under directory: [$(VIRTUALENV_DIR)]"
	@python$(PYTHON_VERSION) -m venv '$(VIRTUALENV_DIR)'

## Configure virtual environment
python/venv: $(VENV_CFG)
.PHONY: python/venv

# -- python venv  export path --
VIRTUALENV_BIN_DIR ?= $(VIRTUALENV_DIR)/bin

# -- python install packages from requirements file --
PYTHON_REQUIREMENTS := requirements.txt
PYTHON_DEV_REQUIREMENTS := requirements-dev.txt
PYTHON_SRC_REQUIREMENTS := $(PYTHON_REQUIREMENTS) $(PYTHON_DEV_REQUIREMENTS)

## Install pips from requirements file(s)
python/packages: $(PYTHON_SRC_REQUIREMENTS)
	@for i in $(^); do \
		echo "[INFO] Installing python dependencies file: [$$i]"; \
		source '$(VIRTUALENV_BIN_DIR)/activate' && \
			pip install -r "$$i"; \
	done
.PHONY: python/packages

## Create virtual environment and install requirements
venv: python/venv python/packages
.PHONY: venv

#-------------------------------------------------------------------------------
# lint
#-------------------------------------------------------------------------------

# -- pylint --
PYLINT_DISABLE_IDS ?= W0511
PYTHON_LINTER_MAX_LINE_LENGTH ?= 100
## Python linter
lint/pylint: $(SRC_DIR)
	-@for i in $(^); do \
		echo "[INFO] running pylint on dir: [$$i]"; \
		$(VIRTUALENV_BIN_DIR)/pylint \
			--max-line-length="$(PYTHON_LINTER_MAX_LINE_LENGTH)" \
			--disable="$(PYLINT_DISABLE_IDS)" \
			"$$i"; \
	done
.PHONY: lint/pylint

# -- flake8 --
## Python styleguide enforcement
lint/flake8: $(SRC_DIR)
	-@for i in $(^); do \
		echo "[INFO] running flake8 on dir: [$$i]"; \
		$(VIRTUALENV_BIN_DIR)/flake8 \
			--max-line-length="$(PYTHON_LINTER_MAX_LINE_LENGTH)" \
			"$$i"; \
	done
.PHONY: lint/flake8

# -- mypy --
## Python static typing
lint/mypy: $(SRC_DIR)
	-@for i in $(^); do \
		echo "[INFO] running mypy on dir: [$$i]"; \
		$(VIRTUALENV_BIN_DIR)/mypy \
			"$$i"; \
	done
.PHONY: lint/mypy

# -- black --
## Python code formatter
lint/black: $(SRC_DIR)
	-@for i in $(^); do \
		echo "[INFO] running black on dir: [$$i]"; \
		$(VIRTUALENV_BIN_DIR)/black \
			--check \
			--diff \
			--line-length="$(PYTHON_LINTER_MAX_LINE_LENGTH)" \
			"$$i"; \
	done
.PHONY: lint/black

# -- bandit --
## Python security linter
lint/bandit: $(SRC_DIR)
	-@for i in $(^); do \
		echo "[INFO] running bandit on dir: [$$i]"; \
		$(VIRTUALENV_BIN_DIR)/bandit \
			--recursive \
			"$$i"; \
	done
.PHONY: lint/bandit

## Run all 'python' linters, validators, and security analyzers
lint/all-python: lint/pylint lint/flake8 lint/mypy lint/black lint/bandit
.PHONY: lint/all-python

## Run all linters, validators, and security analyzers
lint: lint/all-python
.PHONY: lint

#-------------------------------------------------------------------------------
# clean
#-------------------------------------------------------------------------------

## Clean virtual environment directory
clean/venv:
	@[ -d '$(VIRTUALENV_DIR)' ] && rm -rf '$(VIRTUALENV_DIR)/'*
.PHONY: clean/venv

## Clean
clean: clean/venv
.PHONY: clean
