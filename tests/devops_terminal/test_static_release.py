import hashlib,json,pathlib,tempfile,unittest,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from build_static_terminal_release import package,verify
class StaticReleaseTests(unittest.TestCase):
 def test_deterministic_and_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d);m=package(ROOT/"interfaces"/"devops_terminal_client.html",out,"test")
   self.assertTrue(verify(out))
   self.assertEqual(m["admission"],"BLOCKED")
   self.assertEqual(m["ci"],"UNVERIFIED")
   self.assertEqual(m["governance"],"UNVERIFIED")
   self.assertEqual(m["integrity"],"UNVERIFIED")
   self.assertEqual(m,package(ROOT/"interfaces"/"devops_terminal_client.html",out,"test"))
 def test_tamper_detected(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d);m=package(ROOT/"interfaces"/"devops_terminal_client.html",out,"test")
   (out/m["asset"]).write_bytes(b"tampered")
   with self.assertRaisesRegex(ValueError,"ASSET_DIGEST_MISMATCH"):verify(out)
 def test_forged_gate_detected(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d);package(ROOT/"interfaces"/"devops_terminal_client.html",out,"test")
   path=out/"client-release.json";m=json.loads(path.read_text());m["ci"]="PASSED";path.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,"UNATTESTED_RELEASE_GATE"):verify(out)
if __name__=="__main__":unittest.main()
