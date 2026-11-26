import io
import json
import os
import unittest

from client import read_chat_stream

if os.environ.get("LAB_REFERENCE") == "1":
    from reference.request_body import build_request
else:
    from starter.request_body import build_request


class RequestTests(unittest.TestCase):
    def test_streaming_chat(self):
        for model, budget in [("Qwen/Qwen3-0.6B", 32), ("Qwen/Qwen3-4B", 96)]:
            with self.subTest(model=model):
                body = build_request(model, " 解释注意力 ", budget)
                self.assertEqual(body["model"], model)
                self.assertEqual(body["messages"], [{"role": "user", "content": " 解释注意力 "}])
                self.assertEqual(body["max_tokens"], budget)
                self.assertIs(body["stream"], True)
                self.assertEqual(body["temperature"], 0)
                self.assertIs(body["chat_template_kwargs"]["enable_thinking"], False)

    def test_invalid_input(self):
        for args in [(" ", "问题", 1), ("模型", "\n", 1), ("模型", "问题", 0)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                build_request(*args)


class StreamTests(unittest.TestCase):
    def test_text_and_done(self):
        lines = [": heartbeat", "", 'data: {"choices":[{"delta":{"role":"assistant"}}]}']
        for piece in ("你", "好"):
            event = {"choices": [{"delta": {"content": piece}}]}
            lines.append(f"data: {json.dumps(event, ensure_ascii=False)}")
        lines += ['data: {"choices":[]}', "data: [DONE]"]
        self.assertEqual(list(read_chat_stream(io.BytesIO("\r\n".join(lines).encode()))),
                         ["你", "好"])

    def test_interrupted_stream(self):
        with self.assertRaisesRegex(ValueError, "DONE"):
            list(read_chat_stream([]))

    def test_server_error(self):
        with self.assertRaisesRegex(RuntimeError, "service unavailable"):
            list(read_chat_stream([b'data: {"error":"service unavailable"}']))
