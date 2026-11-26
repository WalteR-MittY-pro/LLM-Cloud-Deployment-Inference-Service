import json
import platform
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .doctor import inspect
from .metrics import summary


def write_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def add_row(path, **row):
    with (path / "requests.jsonl").open("a") as out:
        out.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def report(path):
    meta = json.loads((path / "run.json").read_text())
    rows = [json.loads(s) for s in (path / "requests.jsonl").read_text().splitlines()]
    steady = [r for r in rows if r["phase"] == "steady"]
    ok = [r for r in steady if r["status"] == "ok"]
    values = {
        "steady_attempts": len(steady),
        "steady_failures": len(steady) - len(ok),
        "failure_rate": 1 - len(ok) / len(steady) if steady else None,
    }
    measures = ("elapsed_ms", "first_text_ms", "ttft_ms", "tpot_ms", "prefill_ms", "recompute_ms")
    for key in measures:
        values[key] = summary([r[key] for r in ok if r.get(key) is not None])
    write_json(path / "metrics.json", values)
    lines = [
        f"# Day {meta['day']} · {meta['run_id']}",
        "",
        f"状态 {meta['status']} · 来源 {meta['source']} · 退出码 {meta['exit_code']}",
        "",
        f"稳态样本 {len(steady)}，失败 {len(steady) - len(ok)}。",
        "",
        "| 指标（ms） | n | 中位数 | p95 | p99 |",
        "|---|---:|---:|---:|---:|",
    ]
    for key in measures:
        v = values[key]
        lines.append(
            f"| {key} | {v['n']} | {v.get('p50', '—')} | {v.get('p95', '—')} | {v.get('p99', '—')} |"
        )
    lines += ["", f"预热尝试 {sum(r['phase'] == 'warmup' for r in rows)} 次。"]
    windows = [w for w in meta.get("windows", []) if w["phase"] == "steady"]
    if windows:
        seconds = sum(w["seconds"] for w in windows)
        lines.append(f"稳态窗口合计 {seconds:.4f} s，成功吞吐 {len(ok) / seconds:.3f} 请求/s。")
    for row in rows:
        if row["status"] == "failed":
            lines.append(
                f"- {row['phase']} / {row['request_id']}：{row.get('error', '')}；"
                f"已观测首段正文 {row.get('first_text_ms')} ms，token 数 {len(row.get('token_ids', []))}。"
            )
    if meta["error"]:
        lines += ["", meta["error"]]
    (path / "report.md").write_text("\n".join(lines) + "\n")
    return values


@contextmanager
def attempt(root, day, config):
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:10]
    path = Path(root) / f"day-{day}" / run_id
    path.mkdir(parents=True)
    (path / "requests.jsonl").touch()
    (path / "raw.log").touch()
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    meta = {
        "schema_version": 1,
        "day": day,
        "run_id": run_id,
        "started_at": now.isoformat(),
        "git_commit": git.stdout.strip() or None,
        "git_dirty": bool(dirty.stdout),
        "config": config,
        "source": "unverified",
        "model_revision": None,
        "tokenizer_revision": None,
        "environment": {},
        "status": "running",
        "exit_code": None,
        "error": None,
        "command": sys.argv,
        "host_arch": platform.machine(),
    }
    write_json(path / "run.json", meta)
    print(f"RUN={path}", flush=True)
    try:
        meta["environment"] = inspect()
        yield path, meta
    except BaseException as exc:
        meta.update(
            status="failed",
            exit_code=130 if isinstance(exc, KeyboardInterrupt) else 1,
            error=f"{type(exc).__name__}: {exc}",
        )
        with (path / "raw.log").open("a") as out:
            import traceback

            traceback.print_exc(file=out)
        raise
    else:
        meta.update(status="ok", exit_code=0)
    finally:
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(path / "run.json", meta)
        report(path)
