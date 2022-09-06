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

all: venv build docker/build docker/run
.PHONY: all

REPO_NAME ?= $(shell basename $(CURDIR))
SRC_DIR := tfrelease

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

# -- python venv export path --
VIRTUALENV_BIN_DIR ?= $(VIRTUALENV_DIR)/bin

# -- python install packages from requirements file --
PYTHON_REQUIREMENTS := requirements.txt
PYTHON_DEV_REQUIREMENTS := requirements-dev.txt
PYTHON_SRC_REQUIREMENTS := $(PYTHON_REQUIREMENTS) $(PYTHON_DEV_REQUIREMENTS)

## Python install packages from requirements file(s)
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
# build
#-------------------------------------------------------------------------------

DIST_DIR ?= dist

## Build python package
build: $(DIST_DIR) clean/build
	@echo "[INFO] Building python package. Storing artificat in dist directory: [$(DIST_DIR)]"
	@$(VIRTUALENV_BIN_DIR)/python setup.py sdist --dist-dir '${DIST_DIR}'
.PHONY: build

#-------------------------------------------------------------------------------
# publish
#-------------------------------------------------------------------------------

## Python upload check
upload/check:
	@echo "[INFO] Checking whether the long description will render correctly on PyPI."
	@$(VIRTUALENV_BIN_DIR)/twine check --strict dist/*
.PHONY: upload/check

## Python upload package to testpypi
upload/testpypi: upload/check
	@echo "[INFO] Uploading python package to testpypi"
	@$(VIRTUALENV_BIN_DIR)/twine upload --repository testpypi dist/*
.PHONY: upload/testpypi

## Python upload package to pypi
upload/pypi: upload/check
	@echo "[INFO] Uploading python package to pypi"
	@$(VIRTUALENV_BIN_DIR)/twine upload dist/*
.PHONY: upload/pypi

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
# docker
#-------------------------------------------------------------------------------

DOCKER_USER ?= hansohn
DOCKER_REPO ?= tfrelease
DOCKER_TAG ?= latest

## Docker build image
docker/build:
	-@if docker stats --no-stream > /dev/null 2>&1; then \
		echo "[INFO] Building '$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)' docker image."; \
		docker build -t "$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)" .; \
	else \
		echo "[ERROR] Docker 'build' failed. Docker daemon is not Running."; \
	fi
.PHONY: docker/build

## Docker run image
docker/run:
	-@if docker stats --no-stream > /dev/null 2>&1; then \
		echo "[INFO] Running '$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)' docker image"; \
		docker run -it --rm "$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)" bash; \
	else \
		echo "[ERROR] Docker 'run' failed. Docker daemon is not Running."; \
	fi
.PHONY: docker/run

#-------------------------------------------------------------------------------
# clean
#-------------------------------------------------------------------------------

## Clean python build directories
clean/build:
	@echo "[INFO] Cleaning python build directory '$(DIST_DIR)'";
	@[ -d '$(DIST_DIR)' ] && rm -rf '$(DIST_DIR)/'*
.PHONY: clean/build

## Clean docker build images
clean/docker:
	-@if docker stats --no-stream > /dev/null 2>&1; then \
		if docker inspect --type=image "$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)" > /dev/null 2>&1; then \
			echo "[INFO] Removing docker image '$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)'"; \
			docker image rm  "$(DOCKER_USER)/$(DOCKER_REPO):$(DOCKER_TAG)"; \
		fi; \
	fi
.PHONY: clean/docker

## Clean virtual environment directory
clean/venv:
	@echo "[INFO] Cleaning python virtualenv directory '$(VIRTUALENV_DIR)'";
	@[ -d '$(VIRTUALENV_DIR)' ] && rm -rf '$(VIRTUALENV_DIR)/'*
.PHONY: clean/venv

## Clean
clean: clean/build clean/venv clean/docker
.PHONY: clean
