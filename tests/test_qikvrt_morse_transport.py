import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
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

    def test_cli_preserves_existing_destination_for_both_operations(self):
        script = Path(__file__).resolve().parents[1] / "tools/qikvrt_morse_transport.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "source", root / "destination"
            for operation in ("encode", "decode"):
                with self.subTest(operation=operation):
                    source.write_bytes(b"mesh" if operation == "encode" else encode(b"mesh").encode("ascii"))
                    destination.write_bytes(b"original destination")
                    result = subprocess.run([sys.executable, str(script), operation, str(source), str(destination)],
                                            capture_output=True, check=False, timeout=10)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(destination.read_bytes(), b"original destination")

    def test_cli_roundtrip_writes_exact_binary_bytes(self):
        script = Path(__file__).resolve().parents[1] / "tools/qikvrt_morse_transport.py"
        payload = bytes(range(256)) + b"\x00\xffmesh\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, wire, restored = root / "source", root / "wire", root / "restored"
            source.write_bytes(payload)
            for operation, incoming, outgoing in (("encode", source, wire), ("decode", wire, restored)):
                subprocess.run([sys.executable, str(script), operation, str(incoming), str(outgoing)],
                               capture_output=True, check=True, timeout=10)
            self.assertEqual(restored.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
