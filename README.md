# PMFlow
<p style="font-size:15px;">This is a simple process managing tool</p>

<p style="font-size:15px;">This tools keeps the information of the processes it manages in a json file created at it's installation location</p>

## Commands
Create a new process
```
pm create "<your command>"
or
pm create "<your command>" --name "<your process name>"
```
List all managed processes

```
pm ls
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
