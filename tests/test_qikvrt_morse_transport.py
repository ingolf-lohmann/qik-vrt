import unittest
from tools.qikvrt_morse_transport import TransportError, decode, encode


class MorseTransportTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(decode(encode(b"")), b"")

    def test_all_byte_values(self):
        payload = bytes(range(256))
        self.assertEqual(decode(encode(payload)), payload)

    def test_utf8_and_multiframe(self):
        payload = ("QIK-VRT · Δ · 🧭\n" * 19).encode("utf-8")
        self.assertEqual(decode(encode(payload)), payload)

    def test_single_byte_chunks(self):
        self.assertEqual(decode(encode(b"mesh", 1)), b"mesh")

    def test_reordered_frames_rejected(self):
        frames = encode(bytes(range(100))).splitlines(keepends=True)
        frames[0], frames[1] = frames[1], frames[0]
        with self.assertRaises(TransportError):
            decode("".join(frames))

    def test_missing_frame_rejected(self):
        frames = encode(bytes(range(100))).splitlines(keepends=True)
        with self.assertRaises(TransportError):
            decode("".join(frames[:-1]))

    def test_corrupted_symbol_rejected(self):
        text = encode(b"proof")
        changed = ("-" if text[0] == "." else ".") + text[1:]
        with self.assertRaises(TransportError):
            decode(changed)

    def test_missing_terminator_rejected(self):
        with self.assertRaises(TransportError):
            decode(encode(b"proof").rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
