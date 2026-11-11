## Why

There's no way to tell which `arc` is installed. A copy installed from the working folder and the released wheel can carry the same version number but different code; this happened with 0.1.0.

## What Changes

- New `arc --version` flag. It prints the installed version and, when known, where it was installed from: a release file, a local folder, or a git commit.
- Prints to stdout and exits 0, like other `--version` flags.

## Capabilities

### New Capabilities
- `cli-version`: Output of `arc --version`, including install source.

### Modified Capabilities
<!-- none -->

## Impact

- `src/arc/cli.py` only, plus tests. Uses stdlib `importlib.metadata` and the standard install-source record (`direct_url.json`, PEP 610) that pip and uv write.
