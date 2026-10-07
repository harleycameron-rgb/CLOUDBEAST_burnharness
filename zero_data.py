"""Runtime guards for applications that must not access the filesystem."""

import builtins
import io
import os
import stat
import sys
import threading
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


class FileIOViolation(RuntimeError):
    """Raised when guarded application code attempts filesystem access."""


_GUARD_STATE = {
    "active_count": 0,
    "installed": False,
    "patches": None,
    "violations": 0,
}
_GUARD_LOCK = threading.RLock()
_AUDITED_FILESYSTEM_EVENTS = {
    "open", "os.open", "os.listdir", "os.scandir", "os.chdir", "os.fchdir",
    "os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.chmod", "os.chown",
    "os.link", "os.symlink", "os.truncate", "os.utime", "os.read", "os.write",
    "os.pread", "os.pwrite", "os.fsync", "os.fdatasync", "os.ftruncate",
    "os.sendfile", "os.copy_file_range", "os.lstat", "os.access",
    "os.readlink",
}


def _reject_open_regular_files():
    """Fail closed when file descriptors could bypass Python API patches."""
    try:
        descriptors = os.listdir("/proc/self/fd")
    except OSError as exc:
        raise FileIOViolation("cannot verify inherited file descriptors") from exc
    for descriptor in descriptors:
        try:
            fd = int(descriptor)
            if stat.S_ISREG(os.fstat(fd).st_mode):
                raise FileIOViolation(
                    "open regular-file descriptors are disabled in zero-data mode"
                )
        except (OSError, ValueError):
            continue


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
    """Raise on filesystem access, including access through inherited descriptors."""
    entered = False
    try:
        with _GUARD_LOCK:
            if _GUARD_STATE["active_count"] == 0:
                _reject_open_regular_files()
                if not _GUARD_STATE["installed"]:
                    sys.addaudithook(_audit)
                    _GUARD_STATE["installed"] = True
                blocked = (
                    (builtins, "open"),
                    (io, "open"),
                    (os, "open"),
                    (os, "stat"),
                    (os, "lstat"),
                    (os, "access"),
                    (os, "readlink"),
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
                patches = ExitStack()
                try:
                    for target, name in blocked:
                        patches.enter_context(
                            patch.object(target, name, _deny(name), create=True)
                        )
                except Exception:
                    patches.close()
                    raise
                _GUARD_STATE["patches"] = patches
            _GUARD_STATE["active_count"] += 1
            entered = True
            violation_count = _GUARD_STATE["violations"]
        yield
    finally:
        if entered:
            with _GUARD_LOCK:
                _GUARD_STATE["active_count"] -= 1
                if _GUARD_STATE["active_count"] == 0:
                    patches = _GUARD_STATE["patches"]
                    _GUARD_STATE["patches"] = None
                    if patches is not None:
                        patches.close()
                if _GUARD_STATE["violations"] != violation_count:
                    raise FileIOViolation(
                        "filesystem access was attempted in zero-data mode"
                    )
