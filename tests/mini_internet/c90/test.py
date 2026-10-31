import subprocess
import unittest
from pathlib import Path
ROOT=Path(__file__).parent
D='a'*64
class Tests(unittest.TestCase):
 def run_case(self,lines):
  p=subprocess.run([str(ROOT/'authority')],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
  return p.stdout.splitlines()
 def test_happy(self):
  self.assertEqual(self.run_case(['PROPOSE '+D,'OBSERVE '+D,'ACKNOWLEDGE '+D]),['ACCEPT 1 PROPOSE','ACCEPT 2 OBSERVE','ACCEPT 3 ACKNOWLEDGE','STATE 3 1 1'])
 def test_ack_before_observation(self):
  self.assertEqual(self.run_case(['PROPOSE '+D,'ACKNOWLEDGE '+D])[-2:],['REJECT','STATE 1 0 0'])
 def test_mismatched_observation(self):
  self.assertEqual(self.run_case(['PROPOSE '+D,'OBSERVE '+'b'*64,'ACKNOWLEDGE '+D])[-3:],['REJECT','REJECT','STATE 1 0 0'])
 def test_duplicate_ack(self):
  self.assertEqual(self.run_case(['PROPOSE '+D,'OBSERVE '+D,'ACKNOWLEDGE '+D,'ACKNOWLEDGE '+D])[-2:],['REJECT','STATE 3 1 1'])
 def test_second_proposal_rejected(self):
  self.assertEqual(self.run_case(['PROPOSE '+D,'PROPOSE '+'b'*64])[-2:],['REJECT','STATE 1 0 0'])
 def test_invalid_digest(self):
  self.assertEqual(self.run_case(['PROPOSE invalid'])[-2:],['REJECT','STATE 0 0 0'])
if __name__=='__main__': unittest.main()
