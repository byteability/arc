## Context

`arc` is installed with `uv tool install` into its own environment under `uv tool dir`. Releases live in a private GitHub repo, each with a wheel and `SHA256SUMS`. `--version` already reads the PEP 610 install record.

## Goals / Non-Goals

**Goals:** one command to get the latest release safely; refuse rather than guess when the install source is ambiguous; stdlib only.

**Non-Goals:** `--check`, pinning a specific version, downgrades, automatic update checks, updating non-uv installs.

## Decisions

**Subcommand, not flag.** Actions are subcommands (`add`, `restore`); flags only report (`--version`).

**Shell out to `gh` and `uv`.** `gh release view`/`download` reuse the user's GitHub login, so `arc` handles no tokens. `uv tool install --force <wheel>` replaces the installed tool atomically from uv's point of view, which `arc` couldn't do safely for its own running environment. A `_run` helper turns a missing binary or a non-zero exit into `UpdateError` with the tool's stderr. *Alternative:* urllib + `GITHUB_TOKEN`; rejected per the user's choice (token management).

**Confirm it's a uv tool install** by comparing `sys.prefix`'s parent with `uv tool dir`. Otherwise `uv tool install` would create a second, separate copy and the running one wouldn't change.

**Up-to-date check only for release installs.** Only an `archive_info` record means the version number matches a release build. Local and git installs may carry a release's number with different code (the 0.1.0 case), so they need `--force`. Versions are compared as integer `X.Y.Z` tuples; if either doesn't parse, the update proceeds.

**Shared `install` module.** `installed()` returns version, source kind and detail; `version_string()` formats it for `--version`, and `update` uses the kind. This avoids `update` importing `cli`.

**Verification:** reuse `archiver.sha256_file`; parse `SHA256SUMS` lines (`<hash>  <name>`, tolerating `*name`). Downloads go to a `TemporaryDirectory`, removed afterwards.

**Python selection:** pass `--python ">=3.14"` to `uv tool install`, matching the documented install command (older uv may otherwise pick an older interpreter).

## Risks / Trade-offs

- [The repo slug `byteability/arc` is hard-coded] → It's the only distribution channel; a fork would change one constant.
- [Install succeeds but the old process keeps running] → Python has already loaded its modules, so the current run finishes normally; the next run uses the new version.
- [`gh` not logged in or without repo access] → Its error is passed through (e.g. "authentication required").

## Migration Plan

After this is released, users on a working-folder install run `arc update --force` once to switch to release installs; after that, plain `arc update` works.
