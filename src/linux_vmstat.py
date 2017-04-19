#!/usr/bin/env python
#
# igcollect - Linux virtual memory stats
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser(prog='linux_vmstat.py')
    parser.add_argument('--prefix', default='vmstat')
    parser.add_argument(
        '--fields',
        dest='fields',
        default=[],
        nargs='*',
        help='The fields from /proc/vmstat to send',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    vmstat = get_vmstat()
    template = args.prefix + '.{} {} ' + str(int(time()))
    for field in args.fields:
        print(template.format(field, vmstat[field]))


def parse_split_file(filename):
    """Utility to read and parse a space delimited file"""
    with open(filename, 'r') as fd:
        return [line.strip().split(None, 1) for line in fd]


def get_vmstat():
    lines = parse_split_file('/proc/vmstat')
    return {key: int(value.split()[0]) for key, value in lines}


if __name__ == '__main__':
    main()
