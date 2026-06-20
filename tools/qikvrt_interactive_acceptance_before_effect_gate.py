#!/usr/bin/env python3
from __future__ import annotations
import pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main(argv=None):
    text=(ROOT/"qikvrt.cmd").read_text(encoding="utf-8",errors="ignore")
    assert "set /p USER_ACCEPT" in text, "interactive acceptance prompt missing"
    assert "acceptance_persisted" in text, "acceptance persistence missing"
    assert text.find("set /p USER_ACCEPT") < text.find('"event":"command_start"'), "prompt after command_start"
    assert text.find("acceptance_persisted") < text.find('"event":"command_start"'), "persistence after command_start"
    assert "LICENSE_AUTHORSHIP_ACCEPTANCE_DECLINED_IMPORT_BLOCKED" in text, "decline block missing"
    print("PASS interactive acceptance before effect gate")
    return 0
if __name__=="__main__": raise SystemExit(main())
