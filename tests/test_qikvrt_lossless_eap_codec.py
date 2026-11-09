"""Run: python -m unittest discover -s tests -p 'test_qikvrt_lossless_eap_codec.py'"""
import importlib.util
from pathlib import Path
import unittest

module_path = Path(__file__).resolve().parents[1] / "tools" / "qikvrt_lossless_eap_codec.py"
spec = importlib.util.spec_from_file_location("qikvrt_lossless_eap_codec", module_path)
codec = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = codec
spec.loader.exec_module(codec)


class LosslessCodecTests(unittest.TestCase):
    def test_roundtrip_all_byte_values_and_markers(self):
        payload = bytes(range(256)) + b"001100" + bytes(range(255, -1, -1))
        stream = codec.encode(payload)
        decoder = codec.Decoder()
        output = []
        for byte in stream:
            output.extend(decoder.feed(bytes([byte])))
        decoder.finish()
        self.assertEqual([item.payload for item in output], [payload])

    def test_multiple_frames_and_empty_payload(self):
        decoder = codec.Decoder()
        out = decoder.feed(codec.encode(b"") + codec.encode(b"hello"))
        decoder.finish()
        self.assertEqual([x.payload for x in out], [b"", b"hello"])

    def test_integrity_failure(self):
        frame = bytearray(codec.encode(b"abc"))
        frame[-4] ^= 1
        with self.assertRaisesRegex(ValueError, "integrity"):
            codec.Decoder().feed(bytes(frame))

    def test_truncated_frame(self):
        decoder = codec.Decoder()
        decoder.feed(codec.encode(b"abc")[:-1])
        with self.assertRaisesRegex(ValueError, "truncated"):
            decoder.finish()

    def test_oversize_rejected(self):
        with self.assertRaises(ValueError):
            codec.encode(bytes(codec.MAX_PAYLOAD + 1))

    def test_fail_closed_ack(self):
        decoded = codec.Decoder().feed(codec.encode(b"effect"))[0]
        self.assertEqual(codec.acknowledge_effect(
            "e1", decoded, authorized=True, executed=True,
            independently_verified=False).state, "EFFECT_ACK_HOLD")
        self.assertEqual(codec.acknowledge_effect(
            "e1", decoded, authorized=True, executed=True,
            independently_verified=True).state, "EFFECT_ACK_DONE")


if __name__ == "__main__":
    unittest.main()
