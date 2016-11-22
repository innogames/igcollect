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
    return vars(parser.parse_args())


# utility to read and parse a space delimited file (meminfo)
def parse_split_file(filename):
    with open(filename, 'r') as f:
        return [line.strip().split(None, 1) for line in f]


def get_vmstat():
    lines = parse_split_file('/proc/vmstat')
    return {key: int(value.split()[0]) for key, value in lines}


def main(fields):
    vmstat = get_vmstat()
    timestamp = int(time.time())
    hostname = gethostname().replace('.', '_')

    template = "servers.{0}.system.virtualmemory.{1} {2} {3}"
    for field in fields:
        print(template.format(hostname, field, vmstat[field], timestamp))

if __name__ == '__main__':
    main(**parse_args())
