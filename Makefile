.PHONY: venv install install-dev test lint synth deploy destroy create-user login

PYTHON  ?= python3
VENV    := .venv
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest
RUFF    := $(VENV)/bin/ruff

ENV    ?= dev
REGION ?= eu-west-1
TABLE_NAME ?=

CDK_CONTEXT := --context env=$(ENV)
ifneq ($(strip $(TABLE_NAME)),)
CDK_CONTEXT += --context table_name=$(TABLE_NAME)
endif

venv: $(VENV)/bin/python

$(VENV)/bin/python:
	$(PYTHON) -m venv $(VENV)

# Install all dependencies (CDK + Lambda + dev tools)
install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r cdk/requirements.txt -r cdk/requirements-dev.txt -r api/requirements.txt -r requirements-test.txt
	$(PIP) install ruff

# Run tests
test:
	PYTHONPATH=api $(PYTEST) tests/ -v

# Lint and format check
lint:
	$(RUFF) check api/ tests/
	$(RUFF) format --check api/ tests/

# Synthesise CloudFormation templates (no deploy)
synth:
	cdk synth $(CDK_CONTEXT)

# Deploy all stacks to AWS
deploy:
	cdk deploy --all $(CDK_CONTEXT) --require-approval never

# Tear down all stacks from AWS
destroy:
	cdk destroy --all $(CDK_CONTEXT) --force

# Get a JWT token: make login
login:
	@bash scripts/login_user.sh

# Create a Cognito user: make create-user
create-user:
	@ENV=$(ENV) bash scripts/create_user.sh
