#!/usr/bin/env python3
"""igcollect - PSI - Pressure Stall Information

Copyright (c) 2020 InnoGames GmbH
"""

import os
import time

from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser(prog='linux_pressure.py')
    parser.add_argument('--prefix', default='pressure')
    return parser.parse_args()


def main():
    if not os.path.isdir('/proc/pressure'):
        return

    args = parse_args()
    for pressure in get_pressure_stats():
        print('{}.{}'.format(args.prefix, pressure))


def parse_split_file(filename):
    """Utility to read and parse a space delimited file"""
    with open(filename, 'r') as fd:
        return [line.split() for line in fd]


def get_pressure_stats():
    """/proc/pressure/{cpu,memory,io} aggregates the pressure information for
    each of the resource: cpu, memory, and io.

    The format for CPU is as such:
        some avg10=0.00 avg60=0.00 avg300=0.00 total=0
    and for memory and IO:
        some avg10=0.00 avg60=0.00 avg300=0.00 total=0
        full avg10=0.00 avg60=0.00 avg300=0.00 total=0

    The "some" line indicates the share of time in which at least some tasks
    are stalled on a given resource.

    The "full" line indicates the share of time in which all non-idle tasks are
    stalled on a given resource simultaneously. In this state actual CPU cycles
    are going to waste, and a workload that spends extended time in this state
    is considered to be thrashing. This has severe impact on performance, and
    it’s useful to distinguish this situation from a state where some tasks are
    stalled but the CPU is still doing productive work.
    As such, time spent in this subset of the stall state is tracked separately
    and exported in the “full” averages.
    """
    now = int(time.time())
    output = []
    for key in ['cpu', 'io', 'memory']:
        lines = parse_split_file('/proc/pressure/{}'.format(key))
        for line in lines:
            for element in line[1:]:
                name, value = element.split('=', 1)
                output.append('{}.{}.{} {} {}'.format(
                    key, line[0], name, value, now))
    return output


if __name__ == '__main__':
    main()
