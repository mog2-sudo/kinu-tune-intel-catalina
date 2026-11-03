# Intel macOS Catalina compatibility implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement these tasks with verification after each milestone.

**Goal:** Deliver Kinu Tune 0.1.4 VST3 and AU packages targeting Intel macOS 10.15.7.

**Architecture:** Retain the current plug-in identity and audio features. Make Core ML optional and use the existing ONNX CPU vocoder on Catalina. Build ONNX Runtime 1.19.2 from its pinned source for x86_64 / macOS 10.15; its official x86_64 archive requires macOS 11. Package and audit both plug-ins on a GitHub-hosted Intel Mac.

**Tech Stack:** C++17, JUCE, CMake, ONNX Runtime 1.19.2, Python, GitHub Actions, Apple packaging tools.

**Spec:** User request in this chat: the linked v0.1.4 must work on an Intel Mac running macOS 10.15.7. The upstream tag is b0c0a238be90775a181c04e9602323d9ad21c4c8.

## Global Constraints

- Minimum deployment target 10.15; architecture x86_64.
- Preserve the existing 13.0 / Core ML default for normal macOS builds.
- Keep AI resynthesis available through CPU inference.
- Preserve licensing and include modified source with the delivered binaries.
- Do not change the upstream release or shared branches.
- Catalina hardware is unavailable here: report binary compatibility checks separately from an actual Catalina DAW test.

## Review Focus

- A bundled dependency with a newer deployment target must fail the artifact audit.
- CPU builds must not select a Core ML model from an earlier installation.
- AI resynthesis must remain selectable after switching to Classic.
- The installer must allow Intel / 10.15 and install into the user's Library.
- Every non-system dylib must resolve within the distributed plug-in bundle.

### Task 1: Compile the existing audio pipeline for Catalina

**Files:** CMakeLists.txt; cmake/MacOSCompatibility.cmake; Source/Audio/Vocoder.{h,cpp}; Source/Audio/SynthesisEngineType.cpp; tests/ModelInferenceTests.cpp; tests/MacOSCompatibilityTests.cmake; tests/CMakeLists.txt.

**Interfaces:** Add PITCHNET_USE_COREML (BOOL) and PITCHNET_ONNXRUNTIME_ROOT (PATH). CPU builds omit HAVE_COREML. The deployment target remains caller-configurable.

- [x] Add and run compatibility configuration tests: normal defaults remain 13.0/universal/Core ML; x86_64/10.15 defaults to CPU; explicit Core ML below 13.0 is rejected.
- [x] Implement those configuration choices, use a caller-supplied ONNX Runtime, and reject the incompatible official archive on Catalina.
- [ ] Gate Core ML vocoder selection and implementation with HAVE_COREML; report CPU support accurately.
- [ ] Run the existing model inference test on the Intel Mac, including actual GAME / FCPE / vocoder and PSOLA inference, and assert CPU support.

### Task 2: Produce reviewable distribution artifacts

**Files:** .github/workflows/macos-catalina.yml; packaging/macos/build-pkg.sh; packaging/macos/installer/distribution.xml; packaging/INSTALL-macOS-Catalina.txt; tools/macos/check-compatibility.py; tests/test_macos_compatibility.py; MODIFICATIONS.md.

**Interfaces:** The build supplies architecture/minimum OS/source URL to the installer. The audit takes a release folder and rejects incompatible Mach-O files, Core ML dependencies, or unresolved non-system dylibs.

- [x] Add and run tests for the binary auditor with Mach-O fixtures covering compatible/incompatible deployment targets and architectures.
- [x] Build ONNX Runtime at its immutable v1.19.2 source commit with CPU providers and target 10.15; cache only this configuration.
- [ ] Build VST3/AU and the existing tests; run CTest, AU validation, and bundle/installer audits on Intel macOS.
- [ ] Package ZIP, PKG, checksums, verification report, and complete corresponding source (including submodules and runtime source/dependencies).
- [ ] Download the artifacts to F:/KinuTune/dist, inspect their contents and checksums, and obtain an independent final code review.

## Progress and decisions

- Reconnaissance: official ONNX Runtime x86_64 1.19.2 dylib has LC_BUILD_VERSION minos 11.0.0; archive SHA-256 matches upstream's pinned hash.
- Dedicated checkout: this directory was empty; cloned the exact tag and recursive submodules. Work in a new local compatibility branch; a second worktree adds no isolation benefit.
- Execution: continue in this session under the user's build request. No changes to the upstream repository are authorized or needed. Use a private repository on the authenticated account solely to obtain Mac build artifacts.

- Runtime milestone: C++17 CPU runtime built successfully and cached; Intel plug-in/test build in progress in run 41584654065 (source 5c9dffb).
