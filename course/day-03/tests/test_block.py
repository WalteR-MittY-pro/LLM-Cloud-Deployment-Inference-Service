import os
import unittest
import torch
from benchmarks.lessons import lesson
from benchmarks.numerical import compare_official
from mini_engine.model import forward, tiny_model

block = lesson(3, os.getenv("LAB_IMPL", "starter")).decoder_block


class BlockTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(9)
        self.model = tiny_model()

    def test_official_block_logits_and_layer_caches(self):
        result = compare_official(self.model, torch.tensor([[2, 4, 8], [1, 3, 9]]), block)
        self.assertEqual(result["shape"], [2, 3, 64])

    def test_no_future_leakage(self):
        ids = torch.tensor([[2, 4, 8]])
        first, _ = forward(self.model, ids, block=block)
        ids[0, -1] = 15
        second, _ = forward(self.model, ids, block=block)
        torch.testing.assert_close(first[:, :-1], second[:, :-1])
