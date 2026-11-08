"""Stateless, same-origin HTTP boundary for the reviewed local fixture only."""
import json
import sys
import threading

sys.dont_write_bytecode = True

from invariant_harvest import LOCAL_REVISION, local_fixture, verify_evidence
from src.run_supervised_build import _preload_runtime
from zero_data import FileIOViolation

# Program/dependency loading happens before any request enters the guard.
_preload_runtime()
_EXECUTION_LOCK = threading.Lock()
MAX_BODY = 256


def _reply(start_response, status, value):
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    start_response(status, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
    ])
    return [body]


def _fixture_object(pairs):
    if len(pairs) != 1 or pairs[0] != ("fixture", LOCAL_REVISION):
        raise ValueError("fixture object required")
    return dict(pairs)


def app(environ, start_response):
    """No arbitrary samples/uploads, persistent sessions, upstream calls or logs."""
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET")
    if path in ("/runtime", "/api/health") and method == "GET":
        return _reply(start_response, "200 OK", {
            "status": "available", "scope": "synthetic_local_fixture_only",
            "nativeGate": "CLOSED", "persistent_artifacts": False,
            "upstream_verified": False, "fixture": LOCAL_REVISION,
        })
    if path not in ("/api/harvest", "/api/index"):
        return _reply(start_response, "404 Not Found", {"status": "not_found"})
    if method != "POST":
        return _reply(start_response, "405 Method Not Allowed", {"status": "post_required"})
    origin = environ.get("HTTP_ORIGIN")
    scheme = environ.get("HTTP_X_FORWARDED_PROTO", environ.get("wsgi.url_scheme", "https")).split(",")[0].strip()
    expected = scheme + "://" + environ.get("HTTP_HOST", "")
    if (origin is not None and origin != expected
            or environ.get("HTTP_SEC_FETCH_SITE") == "cross-site"):
        return _reply(start_response, "403 Forbidden", {"status": "same_origin_required"})
    if environ.get("CONTENT_TYPE", "").split(";")[0].strip() != "application/json":
        return _reply(start_response, "415 Unsupported Media Type", {"status": "json_fixture_only"})
    try:
        length = int(environ.get("CONTENT_LENGTH", "0"))
    except (TypeError, ValueError):
        length = 0
    if not 0 < length <= MAX_BODY:
        return _reply(start_response, "413 Content Too Large", {"status": "bounded_fixture_request_required"})
    try:
        request = json.loads(environ["wsgi.input"].read(length), object_pairs_hook=_fixture_object)
    except (KeyError, TypeError, ValueError, UnicodeError):
        return _reply(start_response, "400 Bad Request", {"status": "invalid_fixture_request"})
    if request != {"fixture": LOCAL_REVISION}:
        return _reply(start_response, "400 Bad Request", {"status": "unsupported_fixture_request"})
    try:
        # Serialize guarded application work; platform/HTTP handling is outside it.
        with _EXECUTION_LOCK:
            evidence = local_fixture()
            valid = verify_evidence(evidence)
        if not valid or evidence["body"]["retest"]["status"] != "reproduced":
            raise RuntimeError("local fixture rejected")
    except FileIOViolation:
        return _reply(start_response, "503 Service Unavailable", {
            "status": "blocked", "reason": "zero_data_guard_refused_host_environment",
            "nativeGate": "CLOSED", "upstream_verified": False,
        })
    except Exception:
        return _reply(start_response, "503 Service Unavailable", {
            "status": "blocked", "reason": "local_validation_failed",
            "nativeGate": "CLOSED", "upstream_verified": False,
        })
    return _reply(start_response, "200 OK", {
        "status": "local_fixture_reproduced", "nativeGate": "CLOSED",
        "scope": "synthetic_local_fixture_only", "evidence": evidence,
        "local_integrity_checked": True, "upstream_verified": False,
        "persistent_artifacts": False,
    })
