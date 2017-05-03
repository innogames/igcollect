#!/usr/bin/env python
#
# igcollect - Linux NUMA metrics
#
# Copyright (c) 2017, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='numa')
    return parser.parse_args()


def main():
    args = parse_args()
    path = '/sys/devices/system/node/node{}/{}'
    template = args.prefix + '.node{}.{}.{} {} ' + str(int(time()))

    for node in get_numa_nodes():
        with open(path.format(node, 'numastat')) as fd:
            for line in fd:
                key, value = line.strip().split(None, 1)
                print(template.format(node, 'stat', key, value))

        with open(path.format(node, 'meminfo')) as fd:
            for line in fd:
                line_split = line.strip().split()
                key = line_split[2].rstrip(':')
                value = int(line_split[3])
                print(template.format(node, 'memory', key, value))


def parse_split_file(filename):
    """Utility to read and parse a comma delimited file"""
    with open(filename) as fd:
        return [line.strip().split(None, 1) for line in fd]


def get_numa_nodes():
    # Does not support offline nodes separated with ','
    with open('/sys/devices/system/node/online') as fd:
        line = fd.readline().rstrip()

    # Range of nodes
    if '-' not in line:
        # We don't need stats for servers with only one node
        return []

    # Max is exclusive in range so plus 1
    return range(0, int(line.split('-')[1]) + 1)


if __name__ == '__main__':
    main()
