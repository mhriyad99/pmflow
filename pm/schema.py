from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone


class Relation(str, Enum):
    PARENT = 'parent'
    CHILD = 'child'


class Status(str, Enum):
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPED = 'stopped'   # exited cleanly (exit code 0)
    CRASHED = 'crashed'   # exited with non-zero exit code
    UNKNOWN = 'unknown'   # pid reused by OS or state stale


@dataclass
class ProcessRecord:
    pid: int
    command: str
    name: Optional[str]
    group: str
    relation: str
    status: str = Status.RUNNING
    exit_code: Optional[int] = None
    log_file: Optional[str] = None
    autostart: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    exited_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, pid: int, data: dict) -> 'ProcessRecord':
        return cls(
            pid=pid,
            command=data.get('command', ''),
            name=data.get('name'),
            group=data.get('group', ''),
            relation=data.get('relation', Relation.PARENT),
            status=data.get('status', Status.UNKNOWN),
            exit_code=data.get('exit_code'),
            log_file=data.get('log_file'),
            autostart=data.get('autostart', True),
            created_at=data.get('created_at', datetime.now(timezone.utc).isoformat()),
            exited_at=data.get('exited_at'),
        )
