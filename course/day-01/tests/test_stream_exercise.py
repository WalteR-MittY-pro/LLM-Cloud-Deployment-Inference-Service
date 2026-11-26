import os
import unittest

if os.environ.get("LAB_REFERENCE") == "1":
    from reference.stream import read_chat_stream
else:
    from starter.stream import read_chat_stream


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
