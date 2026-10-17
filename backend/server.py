"""Minimal WSGI backend runtime endpoint."""

import json
from datetime import datetime, timezone
from wsgiref.simple_server import make_server


def application(environ, start_response):
    if environ.get("PATH_INFO") != "/runtime":
        body = b'{"status": "not found"}'
        start_response(
            "404 Not Found",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ],
        )
        return [body]

    body = json.dumps(
        {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ).encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


if __name__ == "__main__":
    with make_server("127.0.0.1", 8000, application) as server:
        print("Runtime endpoint listening on http://127.0.0.1:8000/runtime")
        server.serve_forever()
