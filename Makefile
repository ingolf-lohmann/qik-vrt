# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

PYTHON ?= python3

.PHONY: test compile launcher unit conformance security license seed e2e integrity run-api clean

compile:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile qikvrt.py tools/qikvrt_runtime_logger.py tools/qikvrt_subprocess.py tools/qikvrt_initial_acceptance_gate.py tools/qikvrt_integrity.py tools/qikvrt_master_acceptance_gate.py tools/qikvrt_cicd_publish.py tools/qikvrt_seed_common.py tools/qikvrt_validate_state_run.py src/qikvrt_effect_ack.py src/qikvrt_api_handler.py src/qikvrt_github_api_shim.py scripts/qikvrt_api_client.py tests/test_integrity.py tests/test_launcher_runtime.py tests/test_effect_ack_conformance.py tests/test_handler_unit.py tests/test_handler_security.py tests/test_api_client.py tests/test_license_transition.py tests/test_seed_workflows.py tests/test_tcpip_e2e.py

integrity:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tests/test_integrity.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_integrity.py verify

launcher:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tests/test_launcher_runtime.py

unit:
	$(PYTHON) tests/test_handler_unit.py

conformance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest -v tests.test_effect_ack_conformance

security:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest -v tests.test_handler_security tests.test_api_client

license:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_license_transition

seed:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_seed_workflows
	@for script in tools/qikvrt_seed_*.sh; do sh -n "$$script"; done

e2e:
	$(PYTHON) tests/test_tcpip_e2e.py

test: compile integrity launcher conformance unit security license seed e2e
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_integrity.py verify

run-api:
	@test -n "$(QIKVRT_API_TOKEN)" || (echo "BLOCK: set QIKVRT_API_TOKEN" >&2; exit 2)
	@test -n "$(QIKVRT_API_TOKEN_EXPIRES_UTC)" || (echo "BLOCK: set QIKVRT_API_TOKEN_EXPIRES_UTC" >&2; exit 2)
	@test -n "$(QIKVRT_ALLOWED_REPOSITORY)" || (echo "BLOCK: set QIKVRT_ALLOWED_REPOSITORY=owner/repo" >&2; exit 2)
	@test -n "$(QIKVRT_API_PRINCIPAL)" || (echo "BLOCK: set QIKVRT_API_PRINCIPAL" >&2; exit 2)
	PYTHONNOUSERSITE=1 $(PYTHON) -S src/qikvrt_github_api_shim.py

clean:
	rm -rf unit_state e2e_state .qikvrt/runtime .qikvrt/evidence .qikvrt/api logs __pycache__ src/__pycache__ scripts/__pycache__ tests/__pycache__ tools/__pycache__
