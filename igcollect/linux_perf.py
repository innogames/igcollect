#!/usr/bin/env python3
"""
Collect Linux perf metrics

Copyright (c) 2025 InnoGames GmbH
"""

import argparse
import subprocess
import re
import sys
from time import time


def parse_args():
    parser = argparse.ArgumentParser(description="Collect linux perf metrics")
    parser.add_argument(
        "--metrics",
        type=str,
        required=True,
        help="Comma-separated list of perf metrics to collect, see `perf list` for all ones",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=1,
        help="Duration in seconds to collect metrics (default: 1)",
    )
    parser.add_argument(
        "--prefix", type=str, default="perf", help="Metric prefix (default: perf)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Build the perf command
    cmd = [
        "perf",
        "stat",
        "-e",
        args.metrics,
        "-a",  # system-wide
        "--",
        "sleep",
        str(args.duration),
        # a simpler --json output was added in version 6
    ]
    env = {
        "LC_ALL": "C"  # Ensure consistent locale for parsing
    }

    try:
        # Run perf and capture output (perf stat outputs to stderr)
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, check=True
        )
        output = result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running perf: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: perf command not found", file=sys.stderr)
        sys.exit(1)

    # Get current timestamp
    timestamp = int(time())

    # Parse perf output
    # Pattern matches lines like: "         1234      cpu-migrations"
    pattern = r"^\s*([\d,]+)\s+(\S+)"

    for line in output.split("\n"):
        match = re.match(pattern, line)
        if match:
            # Extract value and remove commas
            value = str(match.group(1).replace(",", ""))
            metric_name = match.group(2).replace("-", "_").replace(":", "_")

            # also handle metrics like "cpu_core/cache_misses/"
            metric_name = metric_name.strip("/")
            metric_name = metric_name.replace("/", "_")

            print(f"{args.prefix}.{metric_name} {value} {timestamp}")


if __name__ == "__main__":
    main()
