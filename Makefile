# SPDX-License-Identifier: Apache-2.0
# Origin: QIK-VRT V38 remote format repair and dispatch attestation kit
# Rights-Holder: Ingolf Lohmann
# Project: QIK-VRT
# Source-Code-License: Apache-2.0
# Non-Source-Code-License: CC BY-NC 4.0 for non-code repository materials
# Notice: See RIGHTS.md / QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .q/lic/.
PYTHON ?= python3

.PHONY: test compile unit e2e run-api clean

compile:
	$(PYTHON) -m py_compile src/qikvrt_api_handler.py src/qikvrt_github_api_shim.py scripts/qikvrt_api_client.py tests/test_handler_unit.py tests/test_tcpip_e2e.py

unit:
	$(PYTHON) tests/test_handler_unit.py

e2e:
	$(PYTHON) tests/test_tcpip_e2e.py

test: compile unit e2e

run-api:
	PYTHONNOUSERSITE=1 QIKVRT_API_TOKEN=local-dev-token $(PYTHON) -S src/qikvrt_github_api_shim.py

clean:
	rm -rf unit_state e2e_state .qikvrt/api/inbox/* .qikvrt/api/out/* .qikvrt/api/audit/*.json .qikvrt/api/audit/*.jsonl audit/*.json audit/*.txt
