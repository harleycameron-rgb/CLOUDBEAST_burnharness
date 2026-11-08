"""Local-only preview server. Run after activating the development environment."""
import os
from pathlib import Path
import sys
from wsgiref.simple_server import make_server

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.preview import app


def application(environ, start_response):
    route = environ.get('PATH_INFO', '/')
    static = {'/': ('index.html', 'text/html; charset=utf-8'),
              '/preview.js': ('preview.js', 'text/javascript; charset=utf-8'),
              '/preview.css': ('preview.css', 'text/css; charset=utf-8'),
              '/orrery.html': ('orrery.html', 'text/html; charset=utf-8'),
              '/orrery.js': ('orrery.js', 'text/javascript; charset=utf-8'),
              '/orrery.css': ('orrery.css', 'text/css; charset=utf-8')}
    if route not in static:
        return app(environ, start_response)
    name, content_type = static[route]
    body = (ROOT / 'public' / name).read_bytes()
    start_response('200 OK', [('Content-Type', content_type), ('Cache-Control', 'no-store')])
    return [body]


if __name__ == '__main__':
    with make_server('127.0.0.1', int(os.environ.get('PORT', '8085')), application) as server:
        server.serve_forever()
