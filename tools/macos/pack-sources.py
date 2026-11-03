#!/usr/bin/env python3
"""Archive tracked plug-in/submodule sources and the exact runtime build inputs."""
import pathlib
import subprocess
import sys
import tarfile

root = pathlib.Path(__file__).resolve().parents[2]
output = pathlib.Path(sys.argv[1]).resolve()
runtime = root / ".build-tools/onnxruntime-src"
dependencies = root / ".build-tools/ort-dependency-sources"


def tracked(repository):
    data = subprocess.check_output(["git", "ls-files", "--recurse-submodules", "-z"], cwd=repository)
    return [pathlib.Path(name.decode()) for name in data.split(b"\0") if name]


def source_only(info):
    if ".git" in pathlib.PurePosixPath(info.name).parts:
        return None
    return info


output.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(output, "w:gz", compresslevel=6) as archive:
    for relative in tracked(root):
        archive.add(root / relative, arcname=str(pathlib.Path("kinu-tune") / relative), recursive=False)
    archive.add(root / "Resources/models/GAME", arcname="kinu-tune/Resources/models/GAME", filter=source_only)
    for relative in tracked(runtime):
        archive.add(runtime / relative, arcname=str(pathlib.Path("onnxruntime") / relative), recursive=False)
    if not dependencies.is_dir() or not any(dependencies.iterdir()):
        raise RuntimeError("Missing downloaded ONNX Runtime dependency sources")
    archive.add(dependencies, arcname="onnxruntime-dependency-sources", filter=source_only)
    archive.add(root / ".build-tools/ort-build-info.txt", arcname="ort-build-info.txt")
print(output)
