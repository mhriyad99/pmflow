from typing import Dict

ERROR_CODES: Dict[int, str] = {
    800: "Please specify an existing group of a parent process",
    801: "No parent group with this group name exists. Please specify an existing group of a parent process",
    802: "A group can have only one parent process",
    1000: "No process group with this group name exists",
    1001: "Process not found by name or PID",
    1100: "You must specify exactly one of: PID, group, or --all",
    1200: "You can only specify one of: PID, group, or --all",
    1300: "No log file configured for this process. Use --log-file when creating the process",
    1400: "pmflow.yaml not found in current directory",
    1401: "Invalid pmflow.yaml format",
}


def fmt(code: int) -> str:
    return f"Error {code}: {ERROR_CODES.get(code, 'Unknown error')}"
