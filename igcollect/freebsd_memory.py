#!/usr/bin/env python
"""igcollect - FreeBSD Memory Usage

Copyright (c) 2016 InnoGames GmbH
"""

from __future__ import print_function
from argparse import ArgumentParser
from time import time
import sysctl


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='memory')
    return parser.parse_args()


def parse_memory_info():
    memory_info={}

    memory_info['physmem'] = sysctl.filter('hw.physmem')[0].value
    pagesize = sysctl.filter('hw.pagesize')[0].value

    memory_data = sysctl.filter('vm.stats.vm')
    for line in memory_data:
        name = line.name.split('.')[-1]
        # After multiplying by page size they are not _count anymore
        if name.endswith('_count'):
            name = name.replace('_count', '')
            memory_info[name] = int(line.value) * pagesize

    return memory_info


def main():
    args = parse_args()

    mi = parse_memory_info()
    mem_gap_sys = mi['physmem'] - mi['v_page']

    template = args.prefix + '.{} {} ' + str(int(time()))
    print(template.format('total', mi['physmem']))
    print(template.format('active', mi['v_active']))
    print(template.format('inactive', mi['v_inactive']))
    print(template.format('wired', mi['v_wire']))
    print(template.format('cache', mi['v_cache']))
    print(template.format('free', mi['v_free']))
    print(template.format('gap_sys', mem_gap_sys))

if __name__ == '__main__':
    main()
