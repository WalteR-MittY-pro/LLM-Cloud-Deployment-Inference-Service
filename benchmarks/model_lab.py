from functools import partial
import time

import torch
from transformers import AutoTokenizer, Qwen3ForCausalLM

from mini_engine.model import MODEL_ID, REVISION, attend, forward, tiny_model
from .lessons import lesson
from .metrics import timed, token_metrics
from .numerical import compare_official
from .performance import kv_bytes
from .records import add_row


def measured(fn, device):
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
        baseline = torch.cuda.memory_allocated()
    result, elapsed = timed(fn, device)
    peak = torch.cuda.max_memory_allocated() - baseline if device == "cuda" else None
    return result, elapsed, peak


@torch.inference_mode()
def run(args, path, meta):
    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("未检测到已分配的 CUDA 设备")
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    dtype = getattr(torch, args.dtype)
    meta["source"] = "gpu_measured" if device == "cuda" else "cpu_measured"
    if device == "cuda":
        meta["device_name"] = torch.cuda.get_device_name()
    day = int(args.day)
    if day == 2:
        x = torch.randn(1, args.length, 128, device=device, dtype=dtype)
        w = torch.randn(128, 256, device=device, dtype=dtype)
        project = lesson(2, args.impl).project
        expected = torch.nn.functional.linear(x.float(), w.float().T)

        def experiment(observed):
            y, elapsed, peak = measured(lambda: project(x, w), device)
            tolerance = {torch.float32: 2e-5, torch.float16: 0.03, torch.bfloat16: 0.25}[dtype]
            torch.testing.assert_close(y.float(), expected, atol=tolerance, rtol=tolerance)
            return dict(
                elapsed_ms=elapsed,
                extra_peak_bytes=peak,
                shape=list(y.shape),
                stride=list(x.stride()),
                max_abs_error=(y.float() - expected).abs().max().item(),
            )
    else:
        cold_start = time.perf_counter()
        if args.pretrained or args.checkpoint:
            if args.checkpoint:
                from mini_engine.checkpoint import verify

                verify(args.checkpoint)
            src = args.checkpoint or MODEL_ID
            options = {"local_files_only": True} if args.checkpoint else {"revision": REVISION}
            model = (
                Qwen3ForCausalLM.from_pretrained(src, dtype=dtype, attn_implementation="eager", **options)
                .to(device)
                .eval()
            )
            tokenizer = AutoTokenizer.from_pretrained(src, **options)
            ids = tokenizer(args.prompt, return_tensors="pt").input_ids.to(device)
            meta.update(
                model=MODEL_ID, model_revision=REVISION, tokenizer_revision=REVISION, weights_source=str(src)
            )
        else:
            model = tiny_model().to(device=device, dtype=dtype)
            ids = torch.randint(model.config.vocab_size, (1, args.length), device=device)
            meta.update(model="tiny-random-qwen3", weights_source="seeded_random")
        meta["load_ms"] = (time.perf_counter() - cold_start) * 1000
        block = lesson(3, args.impl).decoder_block
        attention = lesson(4, args.impl).attend if day >= 4 else attend
        step = partial(forward, model, block=block, attention=attention)
        if day == 3:
            alignment = compare_official(model, ids, block)

            def experiment(observed):
                _, elapsed, peak = measured(lambda: step(ids), device)
                return dict(elapsed_ms=elapsed, extra_peak_bytes=peak, **alignment)
        elif day == 4:
            extra = ids[:, -1:]

            def experiment(observed):
                (_, cache), prefill, prefill_peak = measured(lambda: step(ids), device)
                (cached, _), incremental, decode_peak = measured(lambda: step(extra, cache), device)
                (full, _), recompute, full_peak = measured(
                    lambda: step(torch.cat((ids, extra), dim=1)), device
                )
                tol = 3e-5 if dtype == torch.float32 else 0.08
                torch.testing.assert_close(cached[:, -1], full[:, -1], atol=tol, rtol=tol)
                cfg = model.config
                return dict(
                    elapsed_ms=incremental,
                    prefill_ms=prefill,
                    recompute_ms=recompute,
                    prefill_extra_peak_bytes=prefill_peak,
                    decode_extra_peak_bytes=decode_peak,
                    recompute_extra_peak_bytes=full_peak,
                    prompt_tokens=ids.size(1),
                    kv_tensor_bytes=sum(t.nbytes for pair in cache for t in pair),
                    predicted_kv_bytes=kv_bytes(
                        len(cache),
                        cfg.num_key_value_heads,
                        cfg.head_dim,
                        ids.size(1),
                        ids.size(0),
                        model.lm_head.weight.element_size(),
                    ),
                )
        else:
            generation = lesson(5, args.impl).generate
            eos = model.generation_config.eos_token_id
            stop = eos if isinstance(eos, list) else [eos]

            def experiment(observed):
                times, output = [], []
                observed.update(token_ids=output, token_times_ms=times)
                gen = torch.Generator(device=device).manual_seed(args.seed)
                if device == "cuda":
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                    baseline = torch.cuda.memory_allocated()
                start = time.perf_counter()
                for token in generation(
                    step,
                    ids,
                    args.budget,
                    stop,
                    temperature=args.temperature,
                    top_k=args.top_k,
                    top_p=args.top_p,
                    generator=gen,
                ):
                    times.append((time.perf_counter() - start) * 1000)
                    output.append(token)
                row = dict(
                    elapsed_ms=(time.perf_counter() - start) * 1000,
                    token_ids=output,
                    token_times_ms=times,
                    **token_metrics(times),
                )
                if device == "cuda":
                    row["extra_peak_bytes"] = torch.cuda.max_memory_allocated() - baseline
                observed.update(row)
                if args.pretrained or args.checkpoint:
                    row["text"] = tokenizer.decode(output)
                if args.temperature == 0 and args.budget:
                    oracle = model.generate(
                        ids,
                        attention_mask=torch.ones_like(ids),
                        do_sample=False,
                        max_new_tokens=args.budget,
                        pad_token_id=stop[0],
                    )
                    assert oracle[0, ids.size(1) :].tolist() == output, "greedy 与官方生成不一致"
                return row

    for i in range(args.warmup + args.repeat):
        phase = "warmup" if i < args.warmup else "steady"
        observed = {}
        try:
            result = experiment(observed)
        except Exception as exc:
            if "token_times_ms" in observed:
                observed.update(token_metrics(observed["token_times_ms"]))
            add_row(path, request_id=str(i), phase=phase, status="failed", error=str(exc), **observed)
            raise
        add_row(path, request_id=str(i), phase=phase, status="ok", **result)
