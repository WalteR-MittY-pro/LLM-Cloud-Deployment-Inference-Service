DAY ?= 01
ENV ?= cpu
PROFILE ?=
PROFILE_ARG = $(if $(PROFILE),--profile "$(PROFILE)")
DEVICE ?= cpu
IMPL ?= starter
PY = environments/$(ENV)/.venv/bin/python
export PYTHONPATH := $(CURDIR)/src:$(CURDIR)
export LAB_IMPL := $(IMPL)
export LAB_REFERENCE := $(if $(filter reference,$(IMPL)),1,0)
export OMP_NUM_THREADS := 1

.PHONY: setup doctor test check lint lab report render-k8s
setup:
	python3 -m benchmarks.profiles --env "$(ENV)" $(PROFILE_ARG)
	uv sync --locked --project environments/$(ENV) --python 3.12

doctor:
	$(if $(wildcard $(PY)),$(PY),python3) -m benchmarks.run doctor --env "$(ENV)" $(PROFILE_ARG) $(ARGS)

test:
ifeq ($(DAY),00)
	$(PY) -m unittest discover -s environments/lab-topology/tests -v
else
	cd course/day-$(DAY) && "$(CURDIR)/$(PY)" -m unittest discover -s tests -v
endif

lint:
	environments/$(ENV)/.venv/bin/ruff check benchmarks src course tests environments/lab-topology

check: lint
	$(PY) -m unittest discover -s tests -v
	$(PY) -m unittest discover -s environments/lab-topology/tests -v
	@set -e; for day in 01 02 03 04 05; do $(MAKE) test DAY=$$day IMPL=reference; done

lab:
	$(PY) -m benchmarks.run lab --day $(DAY) --env "$(ENV)" $(PROFILE_ARG) --device $(DEVICE) --impl $(IMPL) $(ARGS)

report:
	$(PY) -m benchmarks.run report --run "$(RUN)" $(PROFILE_ARG)

render-k8s:
	@python3 environments/lab-topology/scripts/render_k8s.py $(ARGS)
