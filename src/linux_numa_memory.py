#!/usr/bin/env python3
#
# igcollect - Linux NUMA memory
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
from socket import gethostname


def main():
    timestamp = str(int(time.time()))
    hostname = gethostname().replace('.', '_')
    path = '/sys/devices/system/node/node{}/meminfo'
    template = 'servers.{}.system.numa.node{}.{} {} {}'

    for node in get_numa_nodes():
        with open(path.format(node)) as fd:
            for line in fd:
                line_split = line.strip().split()
                key = line_split[2].rstrip(':')
                value = int(line_split[3])
                print(template.format(hostname, node, key, value, timestamp))


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
