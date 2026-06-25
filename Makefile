.PHONY: install install-dev test lint synth deploy destroy create-user

VENV    := .venv
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest
RUFF    := $(VENV)/bin/ruff

ENV    ?= dev
REGION ?= eu-west-1

# Install all dependencies (CDK + Lambda + dev tools)
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r cdk/requirements.txt -r cdk/requirements-dev.txt -r api/requirements.txt
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
	cdk synth --context env=$(ENV)

# Deploy all stacks to AWS
deploy:
	cdk deploy --all --context env=$(ENV) --require-approval never

# Tear down all stacks from AWS
destroy:
	cdk destroy --all --context env=$(ENV) --force

# Get a JWT token: make login
login:
	@bash scripts/login_user.sh
