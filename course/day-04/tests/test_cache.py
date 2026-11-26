import os
import unittest
import torch
from mini_engine.model import forward, tiny_model
from benchmarks.lessons import lesson


class CacheTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(116)
        self.model = tiny_model()
        self.attend = lesson(4, os.getenv("LAB_IMPL", "starter")).attend

    def step(self, ids, cache=None):
        return forward(self.model, ids, cache, attention=self.attend)

    def test_causal_chunks_and_gqa_cardinality(self):
        ids = torch.tensor([[1, 2, 3, 4, 5, 6]])
        ref = self.model(ids, use_cache=True)
        cache = None
        outputs = []
        for chunk in ids.split([3, 2, 1], dim=1):
            logits, cache = self.step(chunk, cache)
            outputs.append(logits)
        torch.testing.assert_close(torch.cat(outputs, dim=1), ref.logits, atol=2e-5, rtol=2e-5)
        for (k, v), layer in zip(cache, ref.past_key_values.layers, strict=True):
            self.assertEqual(k.shape, (1, 2, 6, 8))
            torch.testing.assert_close(k, layer.keys, atol=2e-5, rtol=2e-5)
            torch.testing.assert_close(v, layer.values, atol=2e-5, rtol=2e-5)

    def test_interleaved_requests_and_unchanged_prefix(self):
        a = torch.tensor([[1, 2]])
        _, prefix = self.step(a)
        snapshot = prefix[0][0].clone()
        _, b = self.step(torch.tensor([[8]]))
        self.step(torch.tensor([[9]]), b)
        x, _ = self.step(torch.tensor([[3, 4]]), prefix)
        y, _ = self.step(torch.tensor([[3, 5]]), prefix)
        ref = self.model(torch.tensor([[1, 2, 3, 4]])).logits
        torch.testing.assert_close(x, ref[:, -2:], atol=2e-5, rtol=2e-5)
        torch.testing.assert_close(x[:, 0], y[:, 0])
        torch.testing.assert_close(prefix[0][0], snapshot)
