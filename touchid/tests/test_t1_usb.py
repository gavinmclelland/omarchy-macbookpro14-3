"""Descriptor fixture is a live dump of this A1707 iBridge (05ac:8600)."""

from pathlib import Path
import os
import subprocess
import sys
import unittest

from t1_relay import verify_transport
from t1_usb import (
    APPLE_VID,
    IBRIDGE_PID,
    find_sep_interface,
    parse_descriptors,
    sep_in_config,
)

FIXTURE = Path(__file__).resolve().parent / "ibridge-descriptors.bin"
DIAGNOSE = Path(__file__).resolve().parent.parent / "t1-touchid-diagnose"
VERIFY = Path(__file__).resolve().parent.parent / "t1-touchid-verify"
RECONFIGURE = Path(__file__).resolve().parent.parent / "t1-sep-reconfigure.sh"
ROOT = Path(__file__).resolve().parents[2]
IBRIDGE = ROOT / "drivers" / "appleibridge" / "apple-ibridge.c"
INSTALL = ROOT / "install.sh"


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

    def test_find_sep_rejects_wrong_vid(self):
        raw = bytearray(self.raw)
        # patch idVendor in the device descriptor (bytes 8-9 of first desc)
        raw[8] = 0x00
        raw[9] = 0x00
        with self.assertRaises(LookupError):
            find_sep_interface(bytes(raw))

    def test_verify_cli_describe_fixture(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(DIAGNOSE.parent)
        proc = subprocess.run(
            [sys.executable, str(DIAGNOSE), "--describe", "--descriptors", str(FIXTURE)],
            cwd=str(DIAGNOSE.parent),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        out = proc.stdout + proc.stderr
        self.assertIn("SEP KernelRelay config=2 iface=7", out)
        self.assertIn("out=0x05 in=0x88", out)
        self.assertIn("sep_in_config2=True", out)

    def test_verify_transport_never_switches_configuration(self):
        sep = find_sep_interface(self.raw)
        self.assertEqual(verify_transport(1, sep), "unavailable")
        self.assertEqual(verify_transport(None, sep), "unavailable")
        self.assertEqual(verify_transport(2, sep), "bulk")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(DIAGNOSE.parent)
        help_out = subprocess.run(
            [sys.executable, str(DIAGNOSE), "--help"],
            cwd=str(DIAGNOSE.parent),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertNotIn("--allow-config2", help_out)
        src = DIAGNOSE.read_text()
        relay = (DIAGNOSE.parent / "t1_relay.py").read_text()
        self.assertNotIn("libusb_set_configuration", relay)
        self.assertNotIn("auto_detach", relay)
        self.assertNotIn("bulk_out", relay)
        self.assertNotIn("control_transfer", relay)
        self.assertNotIn("libusb_set_configuration", src)
        self.assertNotIn("verify-match", src)
        script = RECONFIGURE.read_text()
        self.assertNotIn('echo 2', script)

    def test_legacy_verify_entry_point_always_fails_closed(self):
        for args in ([], ["--probe"], ["--describe"]):
            proc = subprocess.run(
                ["bash", str(VERIFY), *args],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("retired", proc.stderr)

        no_action = subprocess.run(
            [sys.executable, str(DIAGNOSE)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(no_action.returncode, 2)
        self.assertIn("required", no_action.stderr)

    def test_installed_ibridge_driver_cannot_switch_usb_configuration(self):
        src = IBRIDGE.read_text()
        self.assertIn('static char *tb_mode_param = "keyboard";', src)
        self.assertIn("refusing live Touch Bar config switch", src)
        self.assertNotIn("usb_set_configuration(udev", src)
        self.assertNotIn("usb_driver_set_configuration(udev", src)
        self.assertFalse(
            (IBRIDGE.parent / "patches" / "apple-ibridge.patch").exists(),
            "unsafe historical patch must not be reintroduced",
        )
        self.assertIn(
            "refusing unsafe appleibridge source",
            INSTALL.read_text(),
        )

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
