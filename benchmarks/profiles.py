"""Hardware plans. Selecting one is a label, never a resource allocation."""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "environments" / "lab-topology"
PROFILES = tuple(sorted(p.stem for p in (BASE / "profiles").glob("*.json")))
ENVS = ("cpu", "pytorch", "vllm")


def load_profile(name):
    if name is None:
        return None
    if name not in PROFILES:
        raise ValueError(f"Unknown hardware profile: {name}")
    return json.loads((BASE / "profiles" / (name + ".json")).read_text())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=ENVS)
    parser.add_argument("--profile", choices=PROFILES)
    parser.parse_args()
