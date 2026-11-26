import os
import unittest
import torch
from benchmarks.lessons import lesson
from mini_engine.model import forward, tiny_model

runtime = lesson(5, os.getenv("LAB_IMPL", "starter"))


class RuntimeTests(unittest.TestCase):
    def test_greedy_official(self):
        torch.manual_seed(17)
        model = tiny_model()
        ids = torch.tensor([[1, 2, 3]])
        actual = list(runtime.generate(lambda x, c: forward(model, x, c), ids, 5, {63}))
        expected = model.generate(
            ids,
            attention_mask=torch.ones_like(ids),
            do_sample=False,
            max_new_tokens=5,
            eos_token_id=63,
            pad_token_id=63,
        )
        self.assertEqual(actual, expected[0, 3:].tolist())

    def test_stop_and_budget(self):
        for first, budget, expected in [(2, 5, [2]), (3, 5, [3]), (1, 1, [1]), (1, 0, [])]:
            calls = []

            def step(ids, past):
                calls.append(ids.size(1))
                logits = torch.zeros(1, 1, 4)
                logits[:, :, first] = 100
                return logits, ()

            out = list(runtime.generate(step, torch.tensor([[0, 1]]), budget, {2, 3}))
            self.assertEqual(out, expected)
            self.assertEqual(len(calls), len(expected))

    def test_filters_and_seed(self):
        logits = torch.tensor([[1.0, 4.0, 3.0, 2.0]])
        for options in ({"top_k": 1}, {"top_p": 0.1}):
            self.assertEqual(runtime.sample(logits, temperature=1, **options).item(), 1)
        gens = [torch.Generator().manual_seed(4) for _ in range(2)]
        self.assertEqual(*[runtime.sample(logits, temperature=1, generator=g).item() for g in gens])
        with self.assertRaises(ValueError):
            runtime.sample(logits, temperature=1, top_p=0)
