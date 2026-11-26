"""教学 forward：借用 HF 权重容器，不调用其 attention、block 或模型 forward。"""

import math

import torch
import torch.nn.functional as F
from transformers import Qwen3Config, Qwen3ForCausalLM

MODEL_ID = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"


def tiny_model():
    config = Qwen3Config(
        vocab_size=64,
        hidden_size=24,
        intermediate_size=40,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=8,
        max_position_embeddings=4096,
        rope_theta=1_000_000,
        tie_word_embeddings=True,
        eos_token_id=63,
    )
    config._attn_implementation = "eager"
    return Qwen3ForCausalLM(config).eval()


def project(x, weight):
    """[B,S,H] × [H,O] → [B,S,O]。"""
    return x @ weight


def rms(x, weight, eps):
    fp = x.float()
    return (fp * torch.rsqrt(fp.square().mean(-1, keepdim=True) + eps)).to(x.dtype) * weight


def angles(positions, dim, theta, dtype):
    exponent = torch.arange(0, dim, 2, device=positions.device).float() / dim
    phase = positions.float()[:, None] / theta**exponent
    phase = torch.cat((phase, phase), dim=-1)
    return phase.cos().to(dtype), phase.sin().to(dtype)


def rotate(x, cos, sin):
    left, right = x.chunk(2, dim=-1)
    return x * cos + torch.cat((-right, left), dim=-1) * sin


def attend(q, k, v, past=None):
    """q/k/v 为 [batch, heads, new_tokens, head_dim]；缓存按 KV heads 保存。"""
    offset = 0
    if past is not None:
        old_k, old_v = past
        offset = old_k.size(2)
        k = torch.cat((old_k, k), dim=2)
        v = torch.cat((old_v, v), dim=2)
    groups = q.size(1) // k.size(1)
    keys = k.repeat_interleave(groups, dim=1)
    values = v.repeat_interleave(groups, dim=1)
    scores = (q @ keys.transpose(-1, -2)) / math.sqrt(q.size(-1))
    rows = torch.arange(q.size(2), device=q.device) + offset
    cols = torch.arange(k.size(2), device=q.device)
    scores = scores.masked_fill(cols > rows[:, None], float("-inf"))
    probs = scores.softmax(-1, dtype=torch.float32).to(q.dtype)
    return probs @ values, (k, v)


def decoder_block(layer, x, cos, sin, past, attention=attend):
    att = layer.self_attn
    cfg = att.config
    b, s, _ = x.shape
    norm = rms(x, layer.input_layernorm.weight, cfg.rms_norm_eps)

    def heads(projection, count):
        # 本课固定的 Qwen3 配置使用无偏置 Q/K/V 投影。
        projected = project(norm, projection.weight.T)
        return projected.reshape(b, s, count, cfg.head_dim).transpose(1, 2)

    q = rms(heads(att.q_proj, cfg.num_attention_heads), att.q_norm.weight, cfg.rms_norm_eps)
    k = rms(heads(att.k_proj, cfg.num_key_value_heads), att.k_norm.weight, cfg.rms_norm_eps)
    v = heads(att.v_proj, cfg.num_key_value_heads)
    context, cache = attention(rotate(q, cos, sin), rotate(k, cos, sin), v, past)
    x = x + att.o_proj(context.transpose(1, 2).reshape(b, s, -1))
    norm = rms(x, layer.post_attention_layernorm.weight, cfg.rms_norm_eps)
    mlp = layer.mlp
    return x + mlp.down_proj(F.silu(mlp.gate_proj(norm)) * mlp.up_proj(norm)), cache


@torch.inference_mode()
def forward(model, ids, past=None, *, block=decoder_block, attention=attend):
    """等长、无 padding 的稠密 Qwen3；past 由调用者按请求持有。"""
    if ids.ndim != 2 or not ids.size(1):
        raise ValueError("ids 需要非空的 [batch, seq] 输入")
    stack = model.model
    cfg = model.config
    if past is not None and len(past) != len(stack.layers):
        raise ValueError("每层都需要一组 KV")
    offset = past[0][0].size(2) if past is not None else 0
    x = stack.embed_tokens(ids)
    positions = torch.arange(offset, offset + ids.size(1), device=x.device)
    cos, sin = angles(positions, cfg.head_dim, cfg.rope_theta, x.dtype)
    present = []
    for index, layer in enumerate(stack.layers):
        x, kv = block(layer, x, cos, sin, None if past is None else past[index], attention)
        present.append(kv)
    return model.lm_head(rms(x, stack.norm.weight, cfg.rms_norm_eps)), tuple(present)
