import os
import unittest
import torch
from benchmarks.lessons import lesson

project = lesson(2, os.getenv("LAB_IMPL", "starter")).project


class TensorTests(unittest.TestCase):
    def test_hand_computed(self):
        x = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
        w = torch.tensor([[2.0], [3.0]])
        torch.testing.assert_close(project(x, w), torch.tensor([[[8.0], [18.0]]]))

    def test_noncontiguous_batch(self):
        x = torch.arange(24.0).reshape(2, 3, 4).transpose(1, 2)
        w = torch.arange(6.0).reshape(3, 2)
        self.assertFalse(x.is_contiguous())
        torch.testing.assert_close(project(x, w), torch.einsum("bsh,ho->bso", x, w))
