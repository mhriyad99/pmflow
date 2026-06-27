# Incremental Improvement Ideas

**Date:** 2026-06-27  
**Scope:** Additions that fit the existing architecture — one command module, the existing state dict, `psutil`, and `subprocess.Popen`. No daemon process, no server, no new storage engine.

Items marked with the file they touch so it is clear nothing crosses a major boundary.

---

## 1. `pm recreate` — Target a single process or only autostart ones

**Current behaviour:** `pm recreate` restarts every entry in state regardless of context.

**Proposed additions:**

```
pm recreate --name api          # recreate one process by name or PID
pm recreate --auto              # only recreate entries where autostart == true
```

**Where it lands:** `pm/commands/create.py` — `recreate()`.

The function already iterates `state.processes`. Adding a `name_or_pid` argument and an `--auto` flag just adds two `if` conditions to that loop. `autostart` is already stored in every state entry. No schema change needed.

---

## 2. `pm stop --all` and `pm stop --group`

**Current behaviour:** `pm stop` only targets one process. `pm kill` has `--all` and `--group`, but kill is immediate and removes entries. There is no way to gracefully stop a whole group at once.

**Proposed:**

```
pm stop --all
pm stop --group backend
pm stop --group backend --timeout 30
```

**Where it lands:** `pm/commands/stop.py` — `stop()`.

The existing `stop()` function already handles one process. Wrapping it in a loop over `state.get_a_group(group)` or `state.get_processes()` mirrors the pattern already used in `kill.py`'s `_kill_group`. The `_mark_exited` helper already updates state per-entry.

---

## 3. `pm create --cwd <directory>`

**Current behaviour:** spawned processes inherit the working directory of the `pm` process (wherever the terminal was when the command was run). This means recreating processes after a reboot may not work if run from a different directory.

**Proposed:**

```
pm create "python app.py" --name api --cwd /srv/myproject
```

**Where it lands:** `pm/commands/create.py` — `_popen()` and `_create_process()`.

`subprocess.Popen` already accepts `cwd`. Adding `cwd` to `_popen`'s `kwargs` is one line. It needs to be stored in the state entry so `recreate()` and `restart()` can pass it back through. The field defaults to `None` in existing state entries — no migration needed.

---

## 4. `pm export`

**Current behaviour:** `pm up` reads a `pmflow.yaml` and starts processes. The reverse (generating a yaml from current state) does not exist.

**Proposed:**

```
pm export                       # prints pmflow.yaml to stdout
pm export --output pmflow.yaml  # writes to file
```

**Where it lands:** New `pm/commands/export.py`, registered in `main.py`.

`pyyaml` is already a project dependency. The function reads `state.get_processes()`, maps each entry to the yaml structure that `pm up` expects, and calls `yaml.dump`. Roughly 25 lines. Useful when a project was set up interactively with `pm create` and the developer now wants to commit a reproducible config.

---

## 5. `pm info --json`

**Current behaviour:** `pm info` always renders a Rich table. There is no machine-readable output.

**Proposed:**

```
pm info api --json
```

**Where it lands:** `pm/commands/info.py` — `info()`.

The function already builds a `data` dict from state and queries psutil for live stats. Adding `--json` just dumps that dict (plus the live fields) via `json.dumps`. Five lines added. Consistent with `pm ls --json`.

---

## 6. `pm wait <name|pid>`

**Current behaviour:** there is no way to block a script until a managed process exits.

**Proposed:**

```
pm wait api
pm wait api --timeout 60    # error if not done in 60s
```

Exit code mirrors the process: 0 if the process exited cleanly, 1 otherwise. This makes chaining work:

```bash
pm wait build && pm start deploy
```

**Where it lands:** New `pm/commands/wait.py`, registered in `main.py`.

`psutil.Process.wait(timeout)` does exactly this — it blocks until the process exits and returns the exit code. The whole command is a lookup + `proc.wait()` call. Roughly 20 lines.

---

## 7. `pm rename <name|pid> <new-name>`

**Current behaviour:** a process name is set at creation and cannot be changed without editing the state file manually.

**Proposed:**

```
pm rename api api-v2
pm rename 12345 old-api
```

**Where it lands:** New `pm/commands/rename.py`, or added directly to `main.py` as an inline command since it is short enough.

The entire implementation is `state.get_by_name_or_pid` + `state.update_process(pid_str, "name", new_name)`. No subprocess or psutil interaction. Roughly 15 lines. Particularly useful when running `pm up` from a config file and needing to distinguish multiple deployments.

---

## 8. `pm logs --clear`

**Current behaviour:** log files grow indefinitely. There is no way to truncate a log from the CLI.

**Proposed:**

```
pm logs api --clear             # truncate; keep logging to the same file
```

**Where it lands:** `pm/commands/logs.py` — `logs()`.

Opening the file in `"w"` mode and immediately closing it truncates it to zero bytes. The running process keeps writing to the same file descriptor (its stdout/stderr is already open), so logging resumes immediately after the clear. Five lines added to the existing function.

---

## 9. Stale-PID notice in `pm ls`

**Current behaviour:** after a reboot, `pm ls` shows every process as `unknown` with no guidance on what to do.

**Proposed:** after rendering the table, if any entries resolved to `unknown`, print one line at the bottom:

```
2 processes with unknown status. Run `pm cleanup` to remove them or `pm recreate` to restart.
```

**Where it lands:** `pm/commands/ls.py` — `ls()`, after the table render.

Count `unknown` entries from `process_dict` after status resolution. Print only if the count is non-zero and json output is not active. Five lines.

---

## 10. `pm up --dry-run`

**Current behaviour:** `pm up` immediately starts all processes in `pmflow.yaml`. There is no preview mode.

**Proposed:**

```
pm up --dry-run
```

Parses the yaml, sorts parents before children (same as real `pm up`), and prints what would be started without calling `_create_process`:

```
Would start 'api'    → uvicorn app:app --host 0.0.0.0 --port 8000  (parent, group: backend)
Would start 'worker' → celery -A tasks worker                       (child,  group: backend)
```

**Where it lands:** `pm/commands/manage.py` — `up()`.

Add `dry_run: bool = False` parameter. Wrap the `_create_process` call in `if not dry_run`. The print path is a `typer.echo` of the same data the real path uses. Ten lines added.

---

## 11. `pm down --timeout`

**Current behaviour:** `pm down` calls `stop(name)` for each process in `pmflow.yaml` with the hardcoded default timeout of 10 seconds.

**Proposed:**

```
pm down --timeout 30
```

**Where it lands:** `pm/commands/manage.py` — `down()`.

Accept `timeout: int = 10` and thread it through to each `stop(name, timeout=timeout)` call. Three lines changed. Particularly useful for processes with slow shutdown paths (databases, long-lived connections).

---

## 12. `pm config`

**Current behaviour:** a developer who wants to know where the state file or log directory is has to read the source code or the documentation.

**Proposed:**

```
pm config
```

Output:

```
State file   /home/user/.local/share/pmflow/processes_state.json
Log dir      /home/user/.local/state/pmflow/
Data dir     /home/user/.local/share/pmflow/
```

**Where it lands:** `pm/main.py` as an inline command, or a tiny `pm/commands/config.py`.

Imports `DATA_DIR`, `LOG_DIR`, `STATE_FILE` from `pm.settings` and prints them. Roughly 10 lines. Useful during debugging and onboarding.

---

## 13. Auto-discover `pmflow.yaml` in parent directories

**Current behaviour:** `pm up` and `pm down` look for `pmflow.yaml` only in the current working directory.

**Proposed:** if `pmflow.yaml` is not found in CWD, walk up through parent directories (stopping at the filesystem root) before giving error 1400. Same behaviour as how `git` finds `.git`.

```
# Works from any subdirectory of a project
cd /srv/myproject/src
pm up   # finds /srv/myproject/pmflow.yaml
```

**Where it lands:** `pm/commands/manage.py` — a small `_find_config(name)` helper called by both `up()` and `down()`.

```python
def _find_config(name: str) -> Path | None:
    p = Path.cwd()
    while True:
        candidate = p / name
        if candidate.exists():
            return candidate
        if p.parent == p:
            return None
        p = p.parent
```

Roughly 10 lines. Replace the current `Path(config)` existence check with a call to this helper when the given config path does not exist.

---

## 14. systemd backend (Linux servers)

**The idea:** instead of PMFlow trying to supervise processes itself, make systemd the supervisor and PMFlow the ergonomic CLI layer on top of it. You get PMFlow's command style and state tracking; systemd provides crash recovery, boot persistence, journald logging, and resource limits — all for free and battle-tested.

**Proposed:**

```bash
pm create "uvicorn app:app --host 0.0.0.0" --name api --backend systemd
# writes /etc/systemd/system/pmflow-api.service
# runs: systemctl enable pmflow-api && systemctl start pmflow-api

pm stop api       # → systemctl stop pmflow-api
pm restart api    # → systemctl restart pmflow-api
pm logs api       # → journalctl -u pmflow-api --follow
pm ls             # → systemctl is-active for each systemd-backed entry
pm up             # → generates and enables all unit files from pmflow.yaml
pm down           # → systemctl disable + stop, removes unit file
```

The generated unit file:

```ini
[Unit]
Description=PMFlow: api
After=network.target

[Service]
ExecStart=uvicorn app:app --host 0.0.0.0
WorkingDirectory=/srv/myproject
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

`Restart=on-failure` in the unit file is what gives you auto-restart on crash — no daemon or wrapper needed in PMFlow itself.

**What this gives you that the current approach cannot:**

| Capability | Current (direct subprocess) | systemd backend |
|------------|----------------------------|-----------------|
| Auto-restart on crash | No | Yes (`Restart=on-failure`) |
| Survives reboot | No | Yes (`systemctl enable`) |
| Boot persistence | No | Yes |
| Log management | Manual log file | journald (rotated, queryable) |
| Resource limits | No | Yes (`MemoryMax=`, `CPUQuota=`) |
| Dependency ordering | No | Yes (`After=`, `Requires=`) |

**Where it lands:**

New: `pm/backends/systemd.py` (~100 lines) — unit file generation and thin wrappers around `systemctl` and `journalctl`.

Modified: `pm/commands/create.py`, `stop.py`, `ls.py`, `info.py`, `logs.py` — each checks `data.get("backend", "direct")` and routes to the systemd backend or the existing subprocess path. The existing path is untouched; both backends coexist.

New state field: `backend: "direct" | "systemd"` (defaults to `"direct"` for backward compatibility).

**Limitations:**

- Linux only in this form. macOS equivalent is launchd (different API); Windows equivalent is Windows Service Manager + NSSM. A `--backend launchd` or `--backend windows-service` could follow the same pattern later.
- System-level services (`/etc/systemd/system/`) require root. User-level services (`~/.config/systemd/user/`) do not — PMFlow could default to user services and accept a `--system` flag for system-level ones.
- `pm info` would show systemd unit metadata rather than psutil live stats for systemd-backed processes.

---

## What Was Deliberately Left Out

These ideas came up but were set aside because they would require a new background component, a new storage layer, or significant rework of existing logic — none of which counts as incremental:

| Idea | Why it doesn't fit |
|------|--------------------|
| Auto-restart on crash (PMFlow-native) | Needs a long-running watcher or daemon in PMFlow — use the systemd backend instead |
| Log rotation | Needs size polling in the background; journald handles this automatically in the systemd backend |
| Health checks | Background-watcher problem; systemd `ExecStartPost=` and `Type=notify` cover this for the systemd backend |
| Process start ordering with readiness gates (`wait for port 8000`) | Requires polling or hook system far beyond the current `up()` loop |
| Resource limits (CPU cap, memory limit) | Achievable via systemd unit fields (`MemoryMax`, `CPUQuota`) in the systemd backend; no clean cross-platform abstraction otherwise |
| HTTP API / web dashboard | A server is a new component category |
| Multi-machine process management | Needs a network layer and shared state storage |
