#!/usr/bin/env python3
"""Negative controls for mini-internet ZIP admission; no network or secrets."""
import hashlib
import pathlib
import tempfile
import unittest
import zipfile
from verify_bundle import verify

FILES = {
 "mini_internet.py": b"fixture",
 "c90_math_verifier.c": b"fixture",
 "setup_pki.sh": b"fixture",
 "web/app.jsx": b"fixture",
 "out/run1.log": b"RESULT PASS 33 / 33\n",
 "out/run2.log": b"RESULT PASS 33 / 33\n",
 "out/mini-internet-e2e-evidence.json": b"{}",
 "out/cert-thread.txt": b"fixture",
 "out/cert-process.txt": b"fixture",
 "out/cert-interrupt.txt": b"fixture",
 "out/cert-network.txt": b"fixture",
}
def archive(path, payload, extra=None):
    manifest = "".join(hashlib.sha256(v).hexdigest()+"  ./"+k+"\n" for k,v in payload.items())
    with zipfile.ZipFile(path,"w") as z:
        for k,v in payload.items(): z.writestr(k,v)
        z.writestr("SHA256SUMS", manifest)
        if extra: z.writestr(*extra)

class AdmissionTests(unittest.TestCase):
    def test_exact_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"good.zip"
            archive(p,FILES)
            self.assertEqual(verify(p),0)
    def test_unhashed_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"bad.zip"
            archive(p,FILES,("untracked.txt",b"unexpected"))
            with self.assertRaisesRegex(ValueError,"unhashed"): verify(p)
    def test_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"bad.zip"
            archive(p,{k:v for k,v in FILES.items() if k!="web/app.jsx"})
            with self.assertRaisesRegex(ValueError,"missing files"): verify(p)
    def test_fake_pass_log_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"bad.zip"
            archive(p,{**FILES,"out/run2.log":b"RESULT FAIL 0 / 33\n"})
            with self.assertRaisesRegex(ValueError,"test summary"): verify(p)
    def test_changed_payload_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"bad.zip"
            archive(p,FILES)
            with zipfile.ZipFile(p,"a") as z:
                z.writestr("web/app.jsx",b"modified")
            with self.assertRaisesRegex(ValueError,"hash mismatch"): verify(p)

if __name__=="__main__": unittest.main()
