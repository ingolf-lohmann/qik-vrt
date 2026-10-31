#!/usr/bin/env python3
"""Contract tests for fail-closed math gate. Mock verifier is NOT a proof kernel."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).with_name("math_gate.py")

class MathGateTests(unittest.TestCase):
    def scenario(self, mode, expected, attempts=3):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            producer = base / "producer.py"
            producer.write_text("import pathlib,sys\npathlib.Path(sys.argv[2]).write_bytes(b'candidate')\n")
            verifier = base / "verifier.py"
            verifier.write_text(
                "import hashlib,json,pathlib,sys\n"
                "subject=pathlib.Path(sys.argv[1])\n"
                "receipt=pathlib.Path(sys.argv[2])\n"
                "mode="+repr(mode)+"\n"
                "sha=hashlib.sha256(subject.read_bytes()).hexdigest()\n"
                "verdict={'schema':'qikvrt.math-verdict.v1','verdict':"
                "'verified' if mode!='reject' else 'rejected',"
                "'subject_sha256': sha if mode!='wrong_hash' else '0'*64}\n"
                "receipt.write_text(json.dumps(verdict))\n"
                "sys.exit(1 if mode=='exit_nonzero' else 0)\n")
            receipt = base / "gate.json"
            result = subprocess.run([sys.executable, str(GATE),
                "--attempts", str(attempts), "--receipt", str(receipt),
                "--producer", sys.executable, str(producer),
                "--verifier", sys.executable, str(verifier)],
                capture_output=True, text=True, timeout=30)
            data = json.loads(receipt.read_text())
            self.assertEqual(result.returncode == 0, expected, result.stderr)
            self.assertEqual(data["approved"], expected)
            self.assertEqual(len(data["attempts"]), 1 if expected else attempts)
            approved = receipt.with_suffix(".approved.bin")
            self.assertEqual(approved.exists(), expected)
            if expected:
                self.assertEqual(hashlib.sha256(approved.read_bytes()).hexdigest(),
                                 data["subject_sha256"])

    def test_feedback_reaches_producer(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            producer = base / 'producer.py'
            producer.write_text("import json,pathlib,sys\nfeedback=json.loads(pathlib.Path(sys.argv[1]).read_text())\npathlib.Path(sys.argv[2]).write_text('corrected' if feedback['reason']=='verifier_rejected' else 'wrong')\n")
            verifier = base / 'verifier.py'
            verifier.write_text("import hashlib,json,pathlib,sys\ns=pathlib.Path(sys.argv[1]);h=hashlib.sha256(s.read_bytes()).hexdigest()\npathlib.Path(sys.argv[2]).write_text(json.dumps({'schema':'qikvrt.math-verdict.v1','verdict':'verified' if s.read_text()=='corrected' else 'rejected','subject_sha256':h}))\n")
            receipt = base / 'gate.json'
            p = subprocess.run([sys.executable,str(GATE),'--attempts','3','--receipt',str(receipt),'--producer',sys.executable,str(producer),'--verifier',sys.executable,str(verifier)],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            evidence=json.loads(receipt.read_text())
            self.assertEqual([a['reason'] for a in evidence['attempts']],['verifier_rejected','verified'])
            self.assertEqual(receipt.with_suffix('.approved.bin').read_bytes(),b'corrected')

    def test_accept_bound_verdict(self):
        self.scenario("accept", True)
    def test_reject(self):
        self.scenario("reject", False)
    def test_reject_wrong_subject_hash(self):
        self.scenario("wrong_hash", False)
    def test_reject_nonzero_exit_even_with_valid_json(self):
        self.scenario("exit_nonzero", False)

if __name__ == "__main__":
    unittest.main()
