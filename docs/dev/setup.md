# Developer Setup

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.10 | 3.12 recommended (used in CI) |
| uv | any | Recommended; `pip` works too |
| git | any | |

---

## Clone and Install

```bash
git clone https://github.com/mhriyad99/process_manager
cd process_manager
```

**With uv (recommended):**

```bash
uv sync --extra dev
```

`uv.lock` is committed, so `uv sync` reproduces the exact dependency versions used in CI.

**With pip + venv:**

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
.\.venv\Scripts\activate

pip install -e ".[dev]"
```

The `-e` flag installs the package in editable mode — changes to source files take effect immediately without reinstalling.

---

## Verify the Install

```bash
pm version
# pmflow 1.3.0

pm --help
```

---

## Run the Tests

```bash
pytest tests/ -v
```

Run a single file:

```bash
pytest tests/test_create.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=pm --cov-report=term-missing
```

All 43 tests should pass. If they don't, see [Testing](testing.md) for fixture details and common issues.

---

## Project Dependencies

Declared in `pyproject.toml`:

```toml
[project]
dependencies = [
    "typer==0.12.5",
    "click>=7.1.1,<8.2.0",   # pinned: Click 8.2+ broke TyperArgument.make_metavar
    "psutil==6.0.0",
    "platformdirs>=4.0.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "build>=1.5.0",
    "twine>=6.2.0",
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
]
```

**Why Click is pinned below 8.2:** Typer 0.12.5 overrides `Argument.make_metavar()` without a `ctx` parameter. Click 8.2+ added `ctx` to that method's signature, causing a `TypeError` at runtime. The pin will be removable once Typer is upgraded to a version that tracks the Click API change.

---

## Environment Variables

PMFlow has no required environment variables. State and log paths are resolved automatically by `platformdirs`.

| Platform | State file | Log directory |
|----------|-----------|---------------|
| Linux | `~/.local/share/pmflow/processes_state.json` | `~/.local/state/pmflow/` |
| macOS | `~/Library/Application Support/pmflow/processes_state.json` | `~/Library/Logs/pmflow/` |
| Windows | `%APPDATA%\pmflow\processes_state.json` | `%LOCALAPPDATA%\pmflow\Logs\` |

To inspect the state file during development:

```bash
# Linux/macOS
cat ~/.local/share/pmflow/processes_state.json | python -m json.tool

# Windows PowerShell
cat $env:APPDATA\pmflow\processes_state.json
```

---

## Common Dev Tasks

**Wipe state (clean slate for manual testing):**

```bash
pm kill --all
# or directly:
# Linux/macOS
echo '{}' > ~/.local/share/pmflow/processes_state.json
```

**Inspect what a command does without running it:**

```bash
pm create --help
pm stop --help
```

**Add a new dependency:**

```bash
# With uv
uv add <package>
# With pip
pip install <package>
# Then add it manually to pyproject.toml [project.dependencies]
```

**Build the package locally:**

```bash
python -m build
# Outputs dist/pmflow-<version>-py3-none-any.whl
```
