#!/usr/bin/env python3
"""Compatibility entry point for the Day 00 guide; all probes live in benchmarks.doctor."""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from benchmarks.run import main

    sys.argv.insert(1, "doctor")
    main()
