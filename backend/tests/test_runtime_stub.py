import json
import threading
import unittest
from urllib.request import urlopen
from wsgiref.simple_server import make_server

from backend.server import application


class RuntimeStubTests(unittest.TestCase):
    def test_runtime_returns_ok(self):
        with make_server("127.0.0.1", 0, application) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://127.0.0.1:{server.server_port}/runtime") as response:
                    payload = json.load(response)
                    self.assertEqual(response.status, 200)
                    self.assertEqual(payload["status"], "ok")
                    self.assertIn("timestamp", payload)
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
