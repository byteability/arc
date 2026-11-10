## ADDED Requirements

### Requirement: Progress only on an interactive terminal
The system SHALL write progress output to stderr, and only when stderr is a TTY. Progress SHALL never be written to stdout, and stdout output SHALL be unchanged.

#### Scenario: Interactive terminal
- **WHEN** the user runs `arc add ./proj` with stderr attached to a terminal
- **THEN** progress bars are shown on stderr while the command runs

#### Scenario: Not a terminal
- **WHEN** stderr is redirected to a file or pipe
- **THEN** no progress output is written, and stdout is identical to a run without progress

### Requirement: Add phases
`arc add` SHALL report these phases in order: `scanning` (running total of bytes found, no percentage), `compressing` (bytes of regular files read out of the scanned total), `checksum` (archive bytes hashed out of the archive size), and `verifying` (archive bytes read back out of the archive size).

#### Scenario: Phases shown in order
- **WHEN** `arc add ./proj` succeeds on a terminal
- **THEN** stderr shows the `scanning`, `compressing`, `checksum` and `verifying` phases in that order, each ending at 100% except `scanning`

### Requirement: Restore phases
`arc restore` SHALL report `checksum` (archive bytes hashed out of the archive size) and then `extracting` (archive bytes read out of the archive size).

#### Scenario: Phases shown in order
- **WHEN** `arc restore <id>` succeeds on a terminal
- **THEN** stderr shows the `checksum` and then `extracting` phases, each ending at 100%

### Requirement: Progress line format
Each phase SHALL be redrawn in place on a single line showing the phase label, a 20-character bar, the percentage, and processed/total size in human-readable units. A finished phase SHALL end with a newline so it stays visible. Redraws SHALL be throttled to at most 10 per second, except the final 100% redraw.

#### Scenario: Mid-phase line
- **WHEN** 1.2 GB of a 2.3 GB `compressing` phase has been processed
- **THEN** the line reads like `compressing  [██████████░░░░░░░░░░]  52%  1.2 GB/2.3 GB`

#### Scenario: Empty phase
- **WHEN** a phase has a total of 0 bytes (e.g. a folder containing only empty files)
- **THEN** the phase is shown at 100% without errors

### Requirement: Clean output on failure
If a command fails while a progress line is being drawn, the system SHALL end that line with a newline before printing the error message.

#### Scenario: Failure mid-phase
- **WHEN** compression fails partway through on a terminal
- **THEN** the `arc: error:` message starts on its own line, not appended to the progress line
