"""Artifact auditor tests; run with python -m unittest discover -s tests -p test_macos_compatibility.py."""
import importlib.util
import pathlib
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "compatibility", pathlib.Path(__file__).resolve().parents[1] / "tools/macos/check-compatibility.py")
compatibility = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compatibility)


def binary(version=(10, 15, 0), cpu=0x01000007, dependencies=(), rpaths=()):
    commands = []
    if version:
        v = (version[0] << 16) | (version[1] << 8) | version[2]
        commands.append(struct.pack("<IIIIII", 0x32, 24, 1, v, v, 0))
    for name in dependencies:
        value = name.encode() + b"\0"
        size = (24 + len(value) + 7) & ~7
        commands.append(struct.pack("<IIIIII", 0xc, size, 24, 0, 0, 0) + value.ljust(size - 24, b"\0"))
    for name in rpaths:
        value = name.encode() + b"\0"
        size = (12 + len(value) + 7) & ~7
        commands.append(struct.pack("<III", 0x8000001c, size, 12) + value.ljust(size - 12, b"\0"))
    body = b"".join(commands)
    return struct.pack("<IIIIIIII", 0xfeedfacf, cpu, 3, 6, len(commands), len(body), 0, 0) + body


class CompatibilityTests(unittest.TestCase):
    def audit(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "Kinu Tune.vst3/Contents/MacOS/Kinu Tune"
            path.parent.mkdir(parents=True)
            path.write_bytes(data)
            return compatibility.audit_binary(path)

    def test_catalina_intel_is_accepted(self):
        report = self.audit(binary(dependencies=("/usr/lib/libSystem.B.dylib",)))
        self.assertEqual(report["architecture"], "x86_64")
        self.assertEqual(report["minimum_os"], "10.15.0")

    def test_newer_runtime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires macOS 11"):
            self.audit(binary(version=(11, 0, 0)))

    def test_arm_binary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "x86_64"):
            self.audit(binary(cpu=0x0100000c))

    def test_missing_deployment_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "deployment target"):
            self.audit(binary(version=None))

    def test_coreml_dependency_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "CoreML"):
            self.audit(binary(dependencies=("/System/Library/Frameworks/CoreML.framework/Versions/A/CoreML",)))

    def test_build_machine_dependency_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dependency"):
            self.audit(binary(dependencies=("/Users/runner/work/ort/libonnxruntime.dylib",)))

    def test_build_machine_rpath_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "rpath"):
            self.audit(binary(rpaths=("/Users/runner/work/ort",)))

    def test_missing_bundled_runtime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            self.audit(binary(dependencies=("@rpath/libonnxruntime.dylib",), rpaths=("@loader_path/../Frameworks",)))


if __name__ == "__main__":
    unittest.main()
