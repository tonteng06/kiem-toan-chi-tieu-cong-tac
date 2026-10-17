PYTHON ?= python

.PHONY: setup test smoke demo logs eval agent-demo
setup:
	$(PYTHON) -m pip install -r requirements.txt
test:
	$(PYTHON) -m pytest -q
smoke:
	$(PYTHON) scripts/smoke_stdio.py
	$(PYTHON) scripts/smoke_registry.py
	$(PYTHON) scripts/demo_verified_audit.py --transport-only --output logs/transport_smoke.jsonl
demo:
	$(PYTHON) scripts/demo_verified_audit.py
logs:
	$(PYTHON) scripts/demo_verified_audit.py --three
eval:
	$(PYTHON) -m evaluation.evaluate_retrieval
agent-demo:
	$(PYTHON) scripts/demo_agent_mcp.py
