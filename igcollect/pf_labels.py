#!/usr/bin/env python
"""igcollect - FreeBSD Packet Filter

Copyright (c) 2018 InnoGames GmbH
"""

from __future__ import print_function
from argparse import ArgumentParser
from socket import gethostname
from subprocess import check_output
import json
import re
import time

POOL_RE = re.compile("(pool_[0-9]+)_(IP|ip)v([46]).*")


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--prefix", default="network.lbpools.{}".format(gethostname().split(".")[0])
    )
    return parser.parse_args()


def main():
    args = parse_args()
    now = str(int(time.time()))
    anchors = get_anchors()
    labels = get_pf_labels(anchors)
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
        # Split each line by  ' ', this gives is the label name and values
        line_tab = line.split(" ")

        # Cut unnecessary things out of label
        label = line_tab[0].split(":")[0]
        label_re = POOL_RE.match(label)

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

            label_counters[label][proto]["pktsIn"] += int(line_tab[4])
            label_counters[label][proto]["bytesIn"] += int(line_tab[5])
            label_counters[label][proto]["pktsOut"] += int(line_tab[6])
            label_counters[label][proto]["bytesOut"] += int(line_tab[7])
    return label_counters


def get_pf_labels(anchors):
    lines = []
    for anchor in anchors:
        pfctl_result = check_output(
            ["/sbin/pfctl", "-q", "-sl", "-a", anchor],
            universal_newlines=True,
            close_fds=False,
        )
        lines += pfctl_result.splitlines()

    return lines


def get_anchors():
    pfctl_result = check_output(
        ["/sbin/pfctl", "-q", "-sA"],
        universal_newlines=True,
        close_fds=False,
    )

    anchors = [line.strip() for line in pfctl_result.splitlines()]

    return anchors


if __name__ == "__main__":
    main()
