#!/usr/bin/env python
#
# igcollect - Linux memory usage
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
from socket import gethostname
import time, sys

# utility to read and parse a comma delimited file (meminfo)
def parse_split_file(filename):
    try:
        with open(filename, 'r') as f:
            return [line.strip().split(None, 1) for line in f]
    except:
        sys.exit(1)

def get_meminfo():
    lines = parse_split_file('/proc/meminfo')
    # turns ['SwapFree:', '100 kB'] into ('SwapFree', '102400')
    return dict((key[:-1], ( 1024 * int(value.split()[0]))) for key, value in lines)

meminfo = get_meminfo()
timestamp = str(int(time.time()))
hostname = gethostname().replace('.', '_')

# Place for calculated values
meminfo['Apps'] = (meminfo['MemTotal'] - meminfo['MemFree']
                                       - meminfo['Buffers']
                                       - meminfo['Cached']
                                       - meminfo['Slab']
                                       - meminfo['PageTables']
                                       - meminfo['SwapCached'])
meminfo['Swap'] = meminfo['SwapTotal'] - meminfo['SwapFree']

# Define desired fileds for ouput
used_fields = ['Apps', 'PageTables', 'SwapCached', 'VmallocUsed', 'Slab',
               'Cached', 'Buffers', 'MemFree', 'Swap', 'Committed_AS',
               'Mapped', 'Active', 'Inactive']

template = "servers.{0}.system.memory.{1} {2} {3}"
for field in used_fields:
    print(template.format(hostname, field, meminfo[field], timestamp))
