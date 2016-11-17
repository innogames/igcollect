#!/usr/bin/env python
#
# igcollect - Linux memory usage
#
# Copyright (c) 2016, InnoGames GmbH
#

from socket import gethostname
import time


def main():
    meminfo = get_meminfo()
    timestamp = str(int(time.time()))
    hostname = gethostname().replace('.', '_')

    # Place for calculated values
    meminfo['Apps'] = meminfo['MemTotal'] - sum((
        meminfo['MemFree'],
        meminfo['Buffers'],
        meminfo['Cached'],
        meminfo['Slab'],
        meminfo['PageTables'],
        meminfo['SwapCached'],
    ))
    meminfo['Swap'] = meminfo['SwapTotal'] - meminfo['SwapFree']

    # Define desired fields for output
    used_fields = [
        'Apps', 'PageTables', 'SwapCached', 'VmallocUsed', 'Slab',
        'Cached', 'Buffers', 'MemFree', 'Swap', 'Committed_AS',
        'Mapped', 'Active', 'Inactive'
    ]

    template = "servers.{}.system.memory.{} {} {}"
    for field in used_fields:
        print(template.format(hostname, field, meminfo[field], timestamp))


def parse_split_file(filename):
    """Utility to read and parse a comma delimited file"""
    with open(filename) as fd:
        return [line.strip().split(None, 1) for line in fd]


def get_meminfo():
    lines = parse_split_file('/proc/meminfo')
    # turns ['SwapFree:', '100 kB'] into ('SwapFree', '102400')
    return dict(
        (key[:-1], 1024 * int(value.split()[0])) for key, value in lines
    )


if __name__ == '__main__':
    main()
