"""对同一组权重使用两条独立执行路径。"""

import torch
from mini_engine.model import angles, decoder_block, forward


@torch.inference_mode()
def compare_official(model, ids, block=decoder_block, attention=None):
    kw = {"block": block}
    if attention is not None:
        kw["attention"] = attention
    tol = 3e-5 if model.dtype == torch.float32 else 0.08
    captured = []

    def capture(module, args, output):
        captured.append(output.detach())

    handle = model.model.layers[0].register_forward_hook(capture)
    try:
        oracle = model(ids, use_cache=True)
    finally:
        handle.remove()
    x = model.model.embed_tokens(ids)
    pos = torch.arange(ids.size(1), device=ids.device)
    cos, sin = angles(pos, model.config.head_dim, model.config.rope_theta, x.dtype)
    custom_block, _ = block(
        model.model.layers[0],
        x,
        cos,
        sin,
        None,
        **({"attention": attention} if attention is not None else {}),
    )
    torch.testing.assert_close(custom_block, captured[0], atol=tol, rtol=tol)
    ours, cache = forward(model, ids, **kw)
    torch.testing.assert_close(ours, oracle.logits, atol=tol, rtol=tol)
    for (k, v), layer in zip(cache, oracle.past_key_values.layers, strict=True):
        torch.testing.assert_close(k, layer.keys, atol=tol, rtol=tol)
        torch.testing.assert_close(v, layer.values, atol=tol, rtol=tol)
    return {
        "block_max_abs": (custom_block - captured[0]).abs().max().item(),
        "logits_max_abs": (ours - oracle.logits).abs().max().item(),
        "atol": tol,
        "rtol": tol,
        "shape": list(ours.shape),
        "stride": list(ours.stride()),
    }
