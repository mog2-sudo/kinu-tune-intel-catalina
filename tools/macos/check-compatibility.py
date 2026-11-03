#!/usr/bin/env python3
"""Fail closed if a Catalina release contains incompatible Mach-O binaries."""
import argparse
import json
import pathlib
import plistlib
import struct

MAGIC = b"\xcf\xfa\xed\xfe"


def version_string(value):
    return f"{value >> 16}.{(value >> 8) & 255}.{value & 255}"


def audit_binary(path):
    path = pathlib.Path(path)
    data = path.read_bytes()
    if data[:4] != MAGIC or len(data) < 32:
        raise ValueError(f"Expected a thin x86_64 Mach-O: {path}")
    _, cpu, _, _, count, command_bytes, _, _ = struct.unpack_from("<8I", data)
    if cpu != 0x01000007:
        raise ValueError(f"Expected x86_64, found CPU {cpu:#x}: {path}")
    if command_bytes > len(data) - 32:
        raise ValueError(f"Truncated load commands: {path}")
    minimum = None
    dependencies, rpaths = [], []
    offset = 32
    for _ in range(count):
        if offset + 8 > 32 + command_bytes:
            raise ValueError(f"Truncated load command: {path}")
        command, size = struct.unpack_from("<II", data, offset)
        if size < 8 or offset + size > 32 + command_bytes:
            raise ValueError(f"Invalid load command size: {path}")
        if command == 0x32:  # LC_BUILD_VERSION
            platform, minimum, _ = struct.unpack_from("<III", data, offset + 8)
            if platform != 1:
                raise ValueError(f"Expected macOS platform: {path}")
        elif command == 0x24:  # LC_VERSION_MIN_MACOSX
            minimum = struct.unpack_from("<I", data, offset + 8)[0]
        elif command in (0xc, 0x80000018, 0x8000001f, 0x80000023, 0x8000001c):
            start = struct.unpack_from("<I", data, offset + 8)[0]
            if start < 12 or start >= size:
                raise ValueError(f"Invalid library name offset: {path}")
            name = data[offset + start:offset + size].split(b"\0", 1)[0].decode()
            (rpaths if command == 0x8000001c else dependencies).append(name)
        offset += size
    if minimum is None:
        raise ValueError(f"Missing deployment target: {path}")
    if minimum > (10 << 16 | 15 << 8):
        raise ValueError(f"{path} requires macOS {version_string(minimum)}")

    bundle = next((p for p in path.parents if p.suffix in (".vst3", ".component", ".app")), None)
    executable_dir = bundle / "Contents/MacOS" if bundle else path.parent

    def expand(name):
        return pathlib.Path(name.replace("@loader_path", str(path.parent))
                            .replace("@executable_path", str(executable_dir)))

    for rpath in rpaths:
        if not rpath.startswith(("@loader_path", "@executable_path")):
            raise ValueError(f"Non-portable rpath {rpath}: {path}")
    for dependency in dependencies:
        if "CoreML.framework" in dependency:
            raise ValueError(f"Unexpected CoreML dependency: {path}")
        if dependency.startswith(("/System/Library/", "/usr/lib/")):
            continue
        if dependency.startswith("@rpath/"):
            candidates = [expand(rpath) / dependency[len("@rpath/"):] for rpath in rpaths]
            # A dylib inherits the loading executable's Frameworks rpath.
            if bundle:
                candidates.append(bundle / "Contents/Frameworks" / dependency[len("@rpath/"):])
        elif dependency.startswith(("@loader_path/", "@executable_path/")):
            candidates = [expand(dependency)]
        else:
            raise ValueError(f"Non-portable dependency {dependency}: {path}")
        if not any(candidate.is_file() for candidate in candidates):
            raise ValueError(f"Unresolved dependency {dependency}: {path}")
    return {"path": str(path), "architecture": "x86_64",
            "minimum_os": version_string(minimum), "dependencies": dependencies, "rpaths": rpaths}


def audit_release(folder):
    folder = pathlib.Path(folder)
    reports = []
    for bundle_name in ("Kinu Tune.vst3", "Kinu Tune.component"):
        bundle = folder / bundle_name
        with (bundle / "Contents/Info.plist").open("rb") as file:
            info = plistlib.load(file)
        target = tuple(int(n) for n in info["LSMinimumSystemVersion"].split("."))
        if target > (10, 15, 0):
            raise ValueError(f"Info.plist requires a newer macOS: {bundle}")
        if not (bundle / "Contents/MacOS" / info["CFBundleExecutable"]).is_file():
            raise ValueError(f"Missing bundle executable: {bundle}")
        if not (bundle / "Contents/Frameworks/libonnxruntime.dylib").is_file():
            raise ValueError(f"Missing bundled ONNX Runtime: {bundle}")
        for path in sorted(bundle.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            with path.open("rb") as file:
                magic = file.read(4)
            if magic == MAGIC:
                reports.append(audit_binary(path))
            elif magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xfe\xed\xfa\xcf"):
                raise ValueError(f"Expected a thin x86_64 binary: {path}")
    if len(reports) < 4:
        raise ValueError("Expected both plug-in executables and both embedded runtimes")
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_folder")
    arguments = parser.parse_args()
    print(json.dumps(audit_release(arguments.release_folder), indent=2))
