"""统一采用十进制 byte、FLOP、秒。返回值均为理论估算。"""


def weight_bytes(parameters, element_bytes):
    return parameters * element_bytes


def kv_bytes(layers, kv_heads, head_dim, length, batch, element_bytes):
    return 2 * layers * kv_heads * head_dim * length * batch * element_bytes


def gemm_flops(m, n, k):
    return 2 * m * n * k


def roofline(flops, moved_bytes, peak_flops_s, bandwidth_bytes_s):
    return max(flops / peak_flops_s, moved_bytes / bandwidth_bytes_s)


def decode_seconds(parameters, element_bytes, bandwidth_bytes_s, efficiency=1.0):
    if not 0 < efficiency <= 1:
        raise ValueError("效率必须位于 (0, 1]")
    return weight_bytes(parameters, element_bytes) / (bandwidth_bytes_s * efficiency)


def transfer_seconds(payload_bytes, bandwidth_bytes_s, latency_s):
    return latency_s + payload_bytes / bandwidth_bytes_s
