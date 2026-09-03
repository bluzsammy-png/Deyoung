.PHONY: install dev-install test demo demo-gpu demo-multi lint clean

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -q --timeout=90

demo:
	python examples/e2e_demo.py

demo-gpu:
	python examples/e2e_remote_gpu.py

demo-multi:
	python examples/multipurpose_demo.py

demo-zai:
	python examples/zai_tool_spec_example.py

lint:
	ruff check pati_api pati pati_agent pati_workers pati_connectors pati_mcp

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
