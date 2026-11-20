PYTHON ?= python3
CIKS ?=

.PHONY: install test fdic sec load all

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest

fdic:
	$(PYTHON) -m credit_risk.data.download_fdic institutions
	$(PYTHON) -m credit_risk.data.download_fdic financials
	$(PYTHON) -m credit_risk.data.download_fdic failures

# Needs SEC_USER_AGENT set, for example: export SEC_USER_AGENT="Your Name you@example.com"
sec:
	$(PYTHON) -m credit_risk.data.download_sec $(CIKS)

# Loads whatever raw files exist, builds typed tables and runs the checks. Exits 1 on any failure.
load:
	$(PYTHON) -m credit_risk.data.load_warehouse

all: test load
