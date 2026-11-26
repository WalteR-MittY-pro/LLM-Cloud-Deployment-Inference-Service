import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from benchmarks import model_lab


class PartialGenerationTests(unittest.TestCase):
    def test_first_token_survives_later_failure(self):
        def broken(*args, **kwargs):
            yield 17
            raise RuntimeError("decode step two")

        original = model_lab.lesson

        def implementation(day, impl):
            if day == 5:
                return Namespace(generate=broken)
            return original(day, impl)

        args = Namespace(
            day="05",
            device="cpu",
            impl="reference",
            seed=4,
            threads=1,
            dtype="float32",
            pretrained=False,
            checkpoint=None,
            length=3,
            budget=2,
            temperature=0.0,
            top_k=0,
            top_p=1.0,
            warmup=0,
            repeat=1,
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(model_lab, "lesson", implementation):
            path = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "step two"):
                model_lab.run(args, path, {})
            row = json.loads((path / "requests.jsonl").read_text())
        self.assertEqual((row["status"], row["token_ids"]), ("failed", [17]))
        self.assertIsNotNone(row["ttft_ms"])
        self.assertIsNone(row["tpot_ms"])
