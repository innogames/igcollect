#!/usr/bin/env python
"""igcollect - Linux CPU Utilization

Copyright (c) 2025 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time
from typing import Tuple


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--prefix", default="cpu")
    return parser.parse_args()


def main():
    args = parse_args()
    now = str(int(time()))
    header = (
        "user",
        "nice",
        "system",
        "idle",
        "iowait",
        "irq",
        "softirq",
        "steal",
    )
    cpu_data, totals = get_cpustats_dict(header)
    freq_dict = get_cpufreq_dict()

    for cpu in cpu_data:
        for metric in header:
            print(
                "{}.{}.{} {} {}".format(
                    args.prefix, cpu, metric, cpu_data[cpu][metric], now
                )
            )

    # Output CPU frequency information
    for cpu in freq_dict:
        print(
            "{}.{}.frequency {} {}".format(
                args.prefix, cpu, freq_dict[cpu]["frequency"], now
            )
        )

    for value in totals:
        print("{}.{} {} {}".format(args.prefix, value, totals[value], now))


def get_cpustats_dict(header) -> Tuple[dict, dict]:
    """returns aggregated data from /proc/stat"""

    total_dict = {}
    cpustats_dict = {}
    amountCPU = 0

    # headers from /proc/stat CPU stats
    keys = ("user", "nice", "system", "idle", "iowait", "irq", "softirq")

    with open("/proc/stat", "r") as fp:
        for line in fp:
            metric_name = line.split(" ", 1)[0]

            # Here we have to handle some kind of disk first the name than
            # the counters as mentioned in the header.
            if metric_name == "cpu":
                # overall stats
                values = line.split()
                total_dict = dict(zip(keys, values[1:8]))
                if len(line.strip().split()) == 11:
                    total_dict["steal"] = values[8]
                    total_dict["guest"] = values[9]
                    total_dict["guest_nice"] = values[10]
                else:
                    total_dict["steal"] = 0
                    total_dict["guest"] = 0
                    total_dict["guest_nice"] = 0

                # sum all except idle to get CPU time
                total_dict["time"] = sum(
                    int(total_dict[key]) for key in keys if key != "idle"
                )

            elif metric_name.startswith("cpu"):
                # stats per core
                amountCPU += 1
                x = line.strip().split()
                name = x.pop(0).lstrip("cpu")
                cpustats_dict[name] = {}
                for i in header:
                    cpustats_dict[name][i] = x.pop(0)
            elif metric_name == "btime":
                total_dict["uptime"] = int(time()) - int(line.split(" ", 1)[1])
            elif metric_name in [
                "intr",
                "ctxt",
                "processes",
                "procs_running",
                "procs_blocked",
            ]:
                total_dict[metric_name] = int(line.split(" ", 2)[1])

    total_dict["amount"] = amountCPU

    return cpustats_dict, total_dict


def get_cpufreq_dict() -> dict:
    """Returns a dictionary of CPU frequencies from /proc/cpuinfo.

    The dictionary keys are processor IDs (as strings), and the values are
    dictionaries containing the frequency in MHz under the key 'frequency'.
    If the frequency cannot be determined, it defaults to 0.

    Data source: /proc/cpuinfo
    """

    cpufreq_dict = {}
    current_processor = None

    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Parse processor number
                if line.startswith("processor"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        current_processor = parts[1].strip()
                        cpufreq_dict[current_processor] = {"frequency": 0}

                # Parse CPU frequency in MHz
                elif line.startswith("cpu MHz") and current_processor is not None:
                    parts = line.split(":")
                    if len(parts) == 2:
                        try:
                            freq_mhz = float(parts[1].strip())
                            cpufreq_dict[current_processor]["frequency"] = freq_mhz
                        except (ValueError, TypeError):
                            cpufreq_dict[current_processor]["frequency"] = 0

    except (FileNotFoundError, IOError):
        pass

    return cpufreq_dict


if __name__ == "__main__":
    main()
