"""Runtime guards for applications that must not access the filesystem."""

import builtins
import io
import os
import sys
import threading
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


class FileIOViolation(RuntimeError):
    """Raised when guarded application code attempts filesystem access."""


_GUARD_STATE = {"active_count": 0, "installed": False, "violations": 0}
_GUARD_LOCK = threading.RLock()
_AUDITED_FILESYSTEM_EVENTS = {
    "open", "os.open", "os.listdir", "os.scandir", "os.chdir", "os.fchdir",
    "os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.chmod", "os.chown",
    "os.link", "os.symlink", "os.truncate", "os.utime", "os.read", "os.write",
    "os.pread", "os.pwrite", "os.fsync", "os.fdatasync", "os.ftruncate",
    "os.sendfile", "os.copy_file_range",
}


def _audit(event, _args):
    if (_GUARD_STATE["active_count"]
            and event in _AUDITED_FILESYSTEM_EVENTS):
        _GUARD_STATE["violations"] += 1
        raise FileIOViolation(f"filesystem audit event is disabled: {event}")


def _deny(operation):
    def denied(*args, **kwargs):
        if _GUARD_STATE["active_count"]:
            _GUARD_STATE["violations"] += 1
        raise FileIOViolation(f"filesystem operation is disabled: {operation}")
    return denied


@contextmanager
def forbid_file_io():
    """Raise on common Python APIs used for filesystem reads or writes."""
    with _GUARD_LOCK:
        if not _GUARD_STATE["installed"]:
            sys.addaudithook(_audit)
            _GUARD_STATE["installed"] = True
        _GUARD_STATE["active_count"] += 1
        violation_count = _GUARD_STATE["violations"]
    blocked = (
        (builtins, "open"),
        (io, "open"),
        (os, "open"),
        (os, "stat"),
        (os, "listdir"),
        (os, "scandir"),
        (os, "mkdir"),
        (os, "makedirs"),
        (os, "remove"),
        (os, "unlink"),
        (os, "rename"),
        (os, "replace"),
        (os, "rmdir"),
        (os, "chmod"),
        (os, "chown"),
        (os, "link"),
        (os, "symlink"),
        (os, "truncate"),
        (os, "utime"),
        (os, "read"),
        (os, "write"),
        (os, "pread"),
        (os, "pwrite"),
        (os, "fsync"),
        (os, "fdatasync"),
        (os, "ftruncate"),
        (os, "fdopen"),
        (os, "sendfile"),
        (os, "copy_file_range"),
        (os.path, "exists"),
        (os.path, "isfile"),
        (os.path, "isdir"),
        (Path, "open"),
        (Path, "exists"),
        (Path, "stat"),
        (Path, "is_file"),
        (Path, "is_dir"),
        (Path, "iterdir"),
        (Path, "glob"),
        (Path, "rglob"),
        (Path, "samefile"),
        (Path, "read_text"),
        (Path, "read_bytes"),
        (Path, "write_text"),
        (Path, "write_bytes"),
        (Path, "touch"),
        (Path, "mkdir"),
        (Path, "unlink"),
        (Path, "rename"),
        (Path, "replace"),
        (Path, "hardlink_to"),
        (Path, "symlink_to"),
    )
    try:
        with ExitStack() as stack:
            for target, name in blocked:
                stack.enter_context(
                    patch.object(target, name, _deny(name), create=True)
                )
            yield
        if _GUARD_STATE["violations"] != violation_count:
            raise FileIOViolation("filesystem access was attempted in zero-data mode")
    finally:
        with _GUARD_LOCK:
            _GUARD_STATE["active_count"] -= 1
