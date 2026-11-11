## Context

`arc` is installed with `uv tool install` from a release wheel, a git ref, or the working folder. All three can report the same version number.

## Goals / Non-Goals

**Goals:** one-line answer to "which arc is this, and where did it come from?"; stdlib only.

**Non-Goals:** dev version numbers derived from git (would conflict with release-please owning `version`); update checks.

## Decisions

**Read the install source from PEP 610 `direct_url.json`** via `importlib.metadata.distribution("arc").read_text(...)`. pip and uv both write it for direct installs; it's absent for index installs, which then show just the version. *Alternative:* a dynamic version via hatch-vcs; rejected because release-please writes `version` in `pyproject.toml`.

**argparse `action="version"`.** Prints to stdout and exits 0 before the subcommand is required or config is loaded. The string is computed when the parser is built; the cost is one metadata read.

**Defensive parsing.** A missing, malformed or unrecognised record falls back to `arc <version>`; `--version` never fails.

## Risks / Trade-offs

- [Another distribution named `arc` in the same environment would be reported instead] → `uv tool install` gives `arc` its own environment; accepted.
- [The local path shown is where it was installed from, which may have changed since] → It's labelled as the source, not the current state.
