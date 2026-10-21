PY ?= python3
export MPLBACKEND := Agg

.PHONY: install test lint fetch audit multiscale backtest finest stats capacity equities surrogates live figures report all clean docker dirs

install:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src experiments tests

fetch:
	$(PY) -m tfvalidity.cli fetch

audit:
	$(PY) -m tfvalidity.cli audit

multiscale:
	$(PY) -m tfvalidity.cli multiscale

backtest:
	$(PY) -m tfvalidity.cli backtest

finest:
	$(PY) -m tfvalidity.cli finest

stats:
	$(PY) -m tfvalidity.cli stats

capacity:
	$(PY) -m tfvalidity.cli capacity

equities:
	$(PY) -m tfvalidity.cli equities

surrogates:
	$(PY) -m tfvalidity.cli surrogates

live:
	$(PY) -m tfvalidity.cli live

figures:
	$(PY) -m tfvalidity.cli figures

report:
	$(PY) -m tfvalidity.cli report

all: fetch audit multiscale backtest finest stats capacity equities surrogates live figures report

docker: dirs
	docker compose up --build research

dirs:
	mkdir -p data results figures

clean:
	rm -rf .pytest_cache .ruff_cache build *.egg-info
