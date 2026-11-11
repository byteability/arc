## Why

Updating `arc` currently takes four manual commands (find the latest tag, download, verify, reinstall). It's easy to get wrong, as the 0.1.0 working-folder install showed.

## What Changes

- New `arc update` subcommand: installs the latest GitHub release if it's newer than the installed version. It downloads with `gh`, verifies the wheel against the release's `SHA256SUMS`, and reinstalls with `uv tool install --force`.
- `arc update --force` reinstalls the latest release regardless of what's installed.
- Installs from a local folder or git can't be compared by version number. Without `--force`, `arc update` explains this and exits with status 1.
- `arc update` doesn't need `ARCHIVE_DIR`.
- Install-source detection moves from `cli.py` into a new `install` module shared with `--version`. `--version` output is unchanged.

## Capabilities

### New Capabilities
- `self-update`: When `arc update` installs, skips or refuses, and what it verifies first.

### Modified Capabilities
<!-- none: cli-version behavior is unchanged -->

## Impact

- New modules `src/arc/install.py` and `src/arc/update.py`; `cli.py` gains the `update` subcommand.
- Runtime requirements for `arc update` only: `gh` (logged in with access to `byteability/arc`) and `uv` on PATH, and `arc` installed with `uv tool`. Other commands are unaffected; still no Python dependencies.
