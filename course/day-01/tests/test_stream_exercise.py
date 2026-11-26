import os
import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request
import unittest

if os.environ.get("LAB_REFERENCE") == "1":
    from reference.stream import read_chat_stream, open_stream
else:
    from starter.stream import read_chat_stream, open_stream


class StreamExerciseTests(unittest.TestCase):
    def test_fragment_then_failure(self):
        stream = read_chat_stream(
            [
                b":keep-alive",
                b'data: {"choices":[{"delta":{"role":"assistant"}}]}',
                b'data: {"choices":[{"delta":{"content":"two tokens"}}]}',
            ]
        )
        self.assertEqual(next(stream), "two tokens")
        with self.assertRaisesRegex(ValueError, "DONE"):
            next(stream)

    def test_error_and_done(self):
        with self.assertRaisesRegex(RuntimeError, "failed"):
            list(read_chat_stream([b'data: {"error":"failed"}']))
        self.assertEqual(list(read_chat_stream([b"data: [DONE]"])), [])

    def test_http_status_and_error_body(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"budget exceeded")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        raw = io.BytesIO()
        try:
            req = Request(f"http://127.0.0.1:{server.server_port}", data=b"{}")
            with self.assertRaisesRegex(RuntimeError, "400.*budget exceeded"):
                open_stream(req, 2, raw)
            self.assertEqual(raw.getvalue(), b"budget exceeded")
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
