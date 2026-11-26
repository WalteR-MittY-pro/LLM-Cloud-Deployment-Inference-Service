DAY ?= 01
ENV ?= cpu
DEVICE ?= cpu
IMPL ?= starter
PY = environments/$(ENV)/.venv/bin/python
export PYTHONPATH := $(CURDIR)/src:$(CURDIR)
export LAB_IMPL := $(IMPL)
export LAB_REFERENCE := $(if $(filter reference,$(IMPL)),1,0)
export OMP_NUM_THREADS := 1

.PHONY: setup doctor test check lint lab report
setup:
	uv sync --locked --project environments/$(ENV) --python 3.12

doctor:
	$(if $(wildcard $(PY)),$(PY),python3) -m benchmarks.run doctor

test:
	cd course/day-$(DAY) && "$(CURDIR)/$(PY)" -m unittest discover -s tests -v

lint:
	environments/$(ENV)/.venv/bin/ruff check benchmarks src course tests

check: lint
	$(PY) -m unittest discover -s tests -v
	@set -e; for day in 01 02 03 04 05; do $(MAKE) test DAY=$$day IMPL=reference; done

lab:
	$(PY) -m benchmarks.run lab --day $(DAY) --device $(DEVICE) --impl $(IMPL) $(ARGS)

report:
	$(PY) -m benchmarks.run report --run "$(RUN)"
