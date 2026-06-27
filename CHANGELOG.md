# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.0] — 2026-06-27

### Added
- **State file moved to user data directory** (`platformdirs`) — state now survives `pip install --upgrade` and is isolated per user
- **`pm/errors.py`** — centralized error code registry (`fmt(code)` helper)
- **`Status` enum** in `schema.py`: `running`, `paused`, `stopped`, `crashed`, `unknown`
- **`ProcessRecord` dataclass** in `schema.py` — typed schema for process entries with `to_dict` / `from_dict` (backward compatible with old JSON)
- **`pm stop <name|pid>`** — graceful shutdown: SIGTERM → wait → SIGKILL; `--timeout` and `--force` flags
- **`pm restart <name|pid>`** — stop then recreate with same command
- **`pm info <name|pid>`** — detailed view: uptime, CPU %, memory RSS, log path, timestamps
- **`pm logs <name|pid>`** — show last N lines of log; `--follow` for streaming (`tail -f`)
- **`pm cleanup`** — remove all stale (non-running) entries from state
- **`pm up`** / **`pm down`** — start/stop all processes from `pmflow.yaml` config file
- **`pm start`** — alias for `pm create`
- **`pm status`** — alias for `pm ls`
- **`pm version`** — print installed package version
- **`--log-file` / `-l`** option on `pm create` to redirect stdout/stderr to a file
- **`--autostart/--no-autostart`** flag on `pm create` to mark processes for `pm recreate` filtering
- **`--verbose` / `-v`** on `pm create` now prints the log file path
- **Process detachment**: background processes use `start_new_session=True` (Unix) / `DETACHED_PROCESS` (Windows) so they survive terminal close
- **`StateManager.get_by_name_or_pid()`** — look up processes by name or PID string
- **Color-coded status column** in `pm ls` (green/yellow/cyan/red/dim per status)
- **`tests/`** directory with pytest suite covering schema, StateManager, create, kill, ls, stop
- **GitHub Actions CI** (`.github/workflows/test.yml`) — test matrix on Python 3.10–3.13 × Ubuntu/macOS/Windows; auto-publish on version tags
- **`pmflow.yaml`** example config file
- **One-time state migration** from old in-package location to new user data dir on first launch

### Changed
- `pm ls` status resolution now distinguishes `stopped`/`crashed`/`unknown` instead of a generic "doesn't exist"
- `pm kill` refactored into helper functions `_kill_single` / `_kill_group`; error messages use `errors.fmt()`
- `pm create` / `recreate` / `respawn` use `Status` enum constants instead of raw strings
- `pyproject.toml` version bumped to `1.3.0`; added `platformdirs>=4.0.0`, `pyyaml>=6.0.0`, `click>=7.1.1,<8.2.0` (pins Click to a version compatible with Typer 0.12.5 — Click 8.2+ changed `Argument.make_metavar` signature), `pytest`, `pytest-cov` deps
- Removed placeholder `greet` command

### Fixed
- `StateManager.load_state()` now creates parent directories if missing
- `StateManager.update_process()` guards against updating non-existent PIDs

---

## [1.2.16] — 2024-11-26

- Stable release with `create`, `kill`, `ls`, `pause`, `respawn`, `recreate`, group management

## [1.0.1] — 2024-10-21

- Initial stable release
