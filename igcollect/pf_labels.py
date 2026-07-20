#!/usr/bin/env python
"""igcollect - FreeBSD Packet Filter

Copyright © 2026 InnoGames GmbH
"""

import json
import re
import time

from argparse import ArgumentParser
from socket import gethostname
from subprocess import check_output

POOL_RE = re.compile("^(pool_[0-9]+)_(IP|ip)v([46]).*")


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--prefix", default="network.lbpools.{}".format(gethostname().split(".")[0])
    )
    return parser.parse_args()


def main():
    args = parse_args()
    now = str(int(time.time()))
    labels = get_pf_labels()
    label_counters = parse_pf_labels(labels)

    for label in label_counters.keys():
        for proto in ("IPv4", "IPv6"):
            for metric in ("bytesIn", "bytesOut", "pktsIn", "pktsOut"):
                print(
                    "{}.{}.{}.{} {} {}".format(
                        args.prefix,
                        label,
                        proto,
                        metric,
                        label_counters[label][proto][metric],
                        now,
                    )
                )


def parse_pf_labels(labels):
    label_counters = {}

    with open("/etc/iglb/lbpools.json") as jsonfile:
        known_pools = json.load(jsonfile)

    reverse_pools = {}
    for kpk, kpv in known_pools.items():
        nodes = list(kpv.get("nodes", {}).values())
        if not nodes:
            continue
        reverse_pools[kpv["pf_name"]] = kpk

    # Read all lines
    for line in labels:
        # example line:
        # pool_1435231_ipv6:tcp:8081 pool_1435231 45 602 210836 302 125936 300 84900 19

        line_tab = line.split(" ")

        label_re = None
        for label in line_tab:
            # Find the per-address family label
            label_re = POOL_RE.match(label)
            if label_re:
                break

        if label_re:
            label = label_re.group(1)
            if label not in reverse_pools:
                continue
            proto = "IPv" + label_re.group(3)
            label = reverse_pools[label].replace(".", "_")

            if label not in label_counters:
                label_counters[label] = {
                    "IPv4": {
                        "pktsIn": 0,
                        "pktsOut": 0,
                        "bytesIn": 0,
                        "bytesOut": 0,
                    },
                    "IPv6": {
                        "pktsIn": 0,
                        "pktsOut": 0,
                        "bytesIn": 0,
                        "bytesOut": 0,
                    },
                }

            # ignore rule evaluations at [-8]
            # ignore total packets at [-7]
            # ignore total bytes at [-6]
            label_counters[label][proto]["pktsIn"] += int(line_tab[-5])
            label_counters[label][proto]["bytesIn"] += int(line_tab[-4])
            label_counters[label][proto]["pktsOut"] += int(line_tab[-3])
            label_counters[label][proto]["bytesOut"] += int(line_tab[-2])
            # ignore states at [-1]

    return label_counters


def get_pf_labels():
    pfctl_result = check_output(
        ["/sbin/pfctl", "-q", "-sl", "-a", "*"],
        universal_newlines=True,
        close_fds=False,
    )
    return pfctl_result.splitlines()


if __name__ == "__main__":
    main()
