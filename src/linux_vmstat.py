#!/usr/bin/env python
#
# igcollect - Linux virtual memory stats
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
from socket import gethostname
from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser(prog='linux_vmstat.py')
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
    timestamp = int(time.time())
    hostname = gethostname().replace('.', '_')

    template = "servers.{}.system.vmstat.{} {} {}"
    for field in args.fields:
        print(template.format(hostname, field, vmstat[field], timestamp))


def parse_split_file(filename):
    """Utility to read and parse a space delimited file"""
    with open(filename, 'r') as fd:
        return [line.strip().split(None, 1) for line in fd]


def get_vmstat():
    lines = parse_split_file('/proc/vmstat')
    return {key: int(value.split()[0]) for key, value in lines}


if __name__ == '__main__':
    main()
