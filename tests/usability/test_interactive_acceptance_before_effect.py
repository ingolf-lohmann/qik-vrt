#!/usr/bin/env python3
from tests.helpers import repo_path
def test_qikvrt_cmd_prompts_before_command_start():
    text=repo_path("qikvrt.cmd").read_text(encoding="utf-8",errors="ignore")
    assert "set /p USER_ACCEPT" in text
    assert "acceptance_persisted" in text
    assert text.find("set /p USER_ACCEPT") < text.find('"event":"command_start"')
def test_decline_blocks_effect():
    text=repo_path("qikvrt.cmd").read_text(encoding="utf-8",errors="ignore")
    assert "LICENSE_AUTHORSHIP_ACCEPTANCE_DECLINED_IMPORT_BLOCKED" in text
    assert "exit /b 31" in text
def test_acceptance_file_before_effect():
    text=repo_path("qikvrt.cmd").read_text(encoding="utf-8",errors="ignore")
    assert "launcher_acceptance_record.json" in text
    assert text.find("ACCEPTANCE_FILE") < text.find('"event":"command_start"')
