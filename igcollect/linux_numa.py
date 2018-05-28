#!/usr/bin/env python
"""igcollect - Linux NUMA Metrics

Copyright (c) 2017 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time


NUMA_NODES_PATH = '/sys/devices/system/node/online'
NUMA_STAT_PATH = '/sys/devices/system/node/node{}/{}'
CPU_STAT_PATH = '/proc/stat'
CPU_STAT_KEYS = [
    'user',
    'nice',
    'system',
    'idle',
    'iowait',
    'irq',
    'softirq',
]


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='numa')
    return parser.parse_args()


def main():
    args = parse_args()
    nodes = get_numa_nodes()
    template = args.prefix + '.node{}.{}.{} {} ' + str(int(time()))
    cpu_stats = dict(get_cpu_stats())

    for node in nodes:
        cpu_cores = list(get_cpulist(node))
        for index, key in enumerate(CPU_STAT_KEYS):
            print(template.format(node, 'cpu', key, sum(
                int(cpu_stats[c][index]) for c in cpu_cores
            )))

        for key, value in get_numastat(node):
            print(template.format(node, 'stat', key, value))
        for key, value in get_meminfo(node):
            print(template.format(node, 'memory', key, value))


def get_numa_nodes():
    with open(NUMA_NODES_PATH) as fd:
        for node in parse_ranges(fd.read()):
            yield node


def get_cpu_stats():
    with open(CPU_STAT_PATH) as fd:
        for line in fd:
            if not line.startswith('cpu'):
                continue
            cells = line.split()
            core = cells[0][len('cpu'):]
            if not core:
                continue
            yield int(core), cells[1:]


def get_cpulist(node):
    with open(NUMA_STAT_PATH.format(node, 'cpulist')) as fd:
        for cpu_core in parse_ranges(fd.read()):
            yield cpu_core


def get_numastat(node):
    with open(NUMA_STAT_PATH.format(node, 'numastat')) as fd:
        for line in fd:
            yield line.strip().split(None, 1)


def get_meminfo(node):
    with open(NUMA_STAT_PATH.format(node, 'meminfo')) as fd:
        for line in fd:
            line_split = line.strip().split()
            yield line_split[2].rstrip(':'), int(line_split[3])


def parse_ranges(cvs):
    """Expand 0-3,7-11 syntax to explicit list of numbers"""
    for item in cvs.split(','):
        item_split = item.split('-', 1)
        start = int(item_split[0])
        end = int(item_split[-1])

        # Max is exclusive in range so plus 1
        for elem in range(start, end + 1):
            yield elem


if __name__ == '__main__':
    main()
