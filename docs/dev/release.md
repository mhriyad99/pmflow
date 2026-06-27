# Release & CI Guide

## Versioning

PMFlow uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Change type | Version bump |
|-------------|-------------|
| Breaking CLI change, incompatible state schema | MAJOR |
| New commands, new flags, new config fields | MINOR |
| Bug fixes, internal refactors | PATCH |

The version is set in **one place**: `pyproject.toml`:

```toml
[project]
version = "1.3.0"
```

`pm version` reads it at runtime via `importlib.metadata.version("pmflow")`.

---

## Release Checklist

1. **Update `CHANGELOG.md`** — add an `## [X.Y.Z] — YYYY-MM-DD` section with Added / Changed / Fixed entries.
2. **Bump the version** in `pyproject.toml`.
3. **Run the full test suite** locally:
   ```bash
   pytest tests/ -v
   ```
4. **Commit and push** to `main`.
5. **Tag the release**:
   ```bash
   git tag v1.3.1
   git push origin v1.3.1
   ```
6. The GitHub Actions `publish` job triggers automatically on any tag matching `v*` and uploads to PyPI.

---

## CI Pipeline (`.github/workflows/test.yml`)

Two jobs:

### `test`

Runs on every push to `main` and every pull request targeting `main`.

**Matrix:** Python 3.10, 3.11, 3.12, 3.13 × Ubuntu, macOS, Windows = **16 job combinations**.

Steps:
1. Checkout
2. Set up Python
3. `pip install -e ".[dev]"` — installs package + dev dependencies
4. `pytest tests/ -v --tb=short`

All 16 must pass before a PR can be merged.

### `publish`

Runs only when a tag starting with `v` is pushed. Depends on `test` (all 16 must pass first).

Steps:
1. Checkout
2. Set up Python 3.12
3. `pip install build`
4. `python -m build` — produces `dist/pmflow-X.Y.Z-py3-none-any.whl` and `.tar.gz`
5. `pypa/gh-action-pypi-publish` — uploads to PyPI using `PYPI_API_TOKEN` from the `pypi` environment secret

**Required GitHub setup:**
- Create an environment named `pypi` in the repository settings.
- Add a secret `PYPI_API_TOKEN` with a PyPI API token scoped to the `pmflow` project.

---

## Dependency Management

Dependencies are declared in `pyproject.toml`. Lock file is `uv.lock` (committed).

**To reproduce the exact CI environment locally:**

```bash
uv sync --extra dev
```

**To add a runtime dependency:**

```bash
uv add <package>
# or manually edit pyproject.toml, then:
uv lock
```

**To add a dev-only dependency:**

```bash
uv add --dev <package>
```

### Key Constraint

`click>=7.1.1,<8.2.0` is pinned because Typer 0.12.5 overrides `Argument.make_metavar()` without a `ctx` parameter. Click 8.2+ changed the signature of that method, causing a `TypeError` at CLI invocation time.

**To resolve this in the future:** upgrade Typer to a version that supports Click 8.2+ (Typer ≥ 0.13 or later) and remove the upper bound on Click.

---

## Building Locally

```bash
pip install build
python -m build
```

Outputs:
- `dist/pmflow-1.3.0-py3-none-any.whl`
- `dist/pmflow-1.3.0.tar.gz`

To install the wheel locally for end-to-end testing:

```bash
pip install dist/pmflow-1.3.0-py3-none-any.whl --force-reinstall
pm version
```

---

## Manual PyPI Upload (without CI)

```bash
pip install twine
twine upload dist/*
```

You will be prompted for your PyPI username and password (or use `--username __token__ --password <api-token>`).

---

## Platform Notes for CI

| Platform | Known issue |
|----------|-------------|
| Windows | `pm pause` / `pm respawn` use SIGSTOP/SIGCONT which don't exist on Windows; those commands will error. Tests that call `process.send_signal(SIGSTOP)` are not in the suite for this reason. |
| macOS | No known issues. |
| Linux | No known issues. |
