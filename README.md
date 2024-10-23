# PMFlow
<p style="font-size:15px;">This is a simple process managing tool</p>

<p style="font-size:15px;">This tools keeps the information of the processes it manages in a json file created at it's installation location</p>

## Installation
```
pip install pmflow
```
## Commands
create: Creates a new process

Required arguments:
- command: str (default: None)

Optional arguments:
- --name or -n : str (default: None)
- --group or -g : str (default: process_id)
- --relation or -r : "parent" | "child" (default: "parent")
- --verbose or -v: (default: false)
```
pm create "<your command>"
or
pm create "<your command>" --name "<your process name>"
```
ls: List all managed processes

Optional arguments:
- --json or -j (default: false)
```
pm ls
pm ls -j
```
Kill process, kills the process and also removes it from the json file.

```
pm kill <PID>
pm kill-all
```

Recreate all process managed by the tool:
```
pm recreate
```
Pause a process
```
pm pause <PID>
```
respawn all paused process
```
pm respawn-all
```
