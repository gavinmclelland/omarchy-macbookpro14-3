"""Descriptor fixture is a live dump of this A1707 iBridge (05ac:8600)."""

from pathlib import Path
import os
import subprocess
import sys
import unittest

from t1_relay import KRHeader, KR_HEADER_SIZE
from t1_usb import (
    APPLE_VID,
    IBRIDGE_PID,
    find_sep_interface,
    parse_descriptors,
    sep_in_config,
)

FIXTURE = Path(__file__).resolve().parent / "ibridge-descriptors.bin"
VERIFY = Path(__file__).resolve().parent.parent / "t1-touchid-verify"
RECONFIGURE = Path(__file__).resolve().parent.parent / "t1-sep-reconfigure.sh"


class T1UsbTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()

    def test_fixture_is_ibridge_8600(self):
        vid, pid, configs = parse_descriptors(self.raw)
        self.assertEqual(vid, APPLE_VID)
        self.assertEqual(pid, IBRIDGE_PID)
        self.assertEqual({c.value for c in configs}, {1, 2, 3})

    def test_config1_has_no_sep_interface(self):
        self.assertFalse(sep_in_config(self.raw, 1))

    def test_config2_has_kernelrelay_sep(self):
        self.assertTrue(sep_in_config(self.raw, 2))
        sep = find_sep_interface(self.raw)
        self.assertEqual(sep.config, 2)
        self.assertEqual(sep.interface, 7)
        self.assertEqual(sep.ep_out, 0x05)
        self.assertEqual(sep.ep_in, 0x88)

    def test_kernelrelay_header_roundtrip(self):
        hdr = KRHeader(b"CMD\x00", 3, 1, 0x1122334455667788, 0xA, 32, 16)
        blob = hdr.pack()
        self.assertEqual(len(blob), KR_HEADER_SIZE)
        back = KRHeader.unpack(blob)
        self.assertEqual(back.fourcc, b"CMD\x00")
        self.assertEqual(back.msg_index, 3)
        self.assertEqual(back.has_buffer, 1)
        self.assertEqual(back.reply_to, 0x1122334455667788)
        self.assertEqual(back.cmd, 0xA)
        self.assertEqual(back.msg_length, 32)
        self.assertEqual(back.data_length, 16)

    def test_find_sep_rejects_wrong_vid(self):
        raw = bytearray(self.raw)
        # patch idVendor in the device descriptor (bytes 8-9 of first desc)
        raw[8] = 0x00
        raw[9] = 0x00
        with self.assertRaises(LookupError):
            find_sep_interface(bytes(raw))

    def test_verify_cli_describe_fixture(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(VERIFY.parent)
        proc = subprocess.run(
            [sys.executable, str(VERIFY), "--describe", "--descriptors", str(FIXTURE)],
            cwd=str(VERIFY.parent),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        out = proc.stdout + proc.stderr
        self.assertIn("SEP KernelRelay config=2 iface=7", out)
        self.assertIn("out=0x05 in=0x88", out)
        self.assertIn("sep_in_config2=True", out)

    def test_reconfigure_script_refuses_set_configuration(self):
        proc = subprocess.run(
            ["bash", str(RECONFIGURE)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("deadlocks iBridge USB", proc.stderr)


if __name__ == "__main__":
    unittest.main()
