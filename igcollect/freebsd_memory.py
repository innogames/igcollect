#!/usr/bin/env python
"""igcollect - FreeBSD Memory Usage

Copyright (c) 2024 InnoGames GmbH
"""

import re
from argparse import ArgumentParser
from time import time
import sysctl

UMA_STATS = ('size', 'stats.frees', 'stats.allocs', 'stats.current')

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='memory')
    return parser.parse_args()


def main():
    args = parse_args()
    now = str(int(time()))

    mi = parse_memory_info()
    mem_gap_sys = mi['physmem'] - mi['v_page']

    template = args.prefix + '.{} {} ' + now
    print(template.format('total', mi['physmem']))
    print(template.format('active', mi['v_active']))
    print(template.format('inactive', mi['v_inactive']))
    print(template.format('wired', mi['v_wire']))
    print(template.format('cache', mi['v_cache']))
    print(template.format('free', mi['v_free']))
    print(template.format('gap_sys', mem_gap_sys))

    ui = parse_uma_info()
    for zone, data in ui.items():
        for metric, value in data.items():
            print(template.format(f'uma.{zone}.{metric}', value))


# Fix for missing long types
def parse_sysctl_value(a):
    if type(a.value) == bytearray:
        return int.from_bytes(a.value, byteorder='little', signed=False)
    return a.value


def parse_uma_info():
    uma_info = {}

    # The sysctl python module does not seem to dig into sysctl data correctly.
    # It retrieves all OIDs with proper names but the values are always None.
    # Fetch the list once, build the list of known UMA zones.
    for line in sysctl.filter('vm.uma'):
        s = line.name.split('.')
        if len(s) == 3:
            uma_info[s[2]] = {}

    # Fetch the real data in a separate step only for wanted OIDs.
    for oid in uma_info.keys():
        for metric in UMA_STATS:
            for line in sysctl.filter(f'vm.uma.{oid}.{metric}'):
                uma_info[oid][metric] = parse_sysctl_value(line)
        uma_info[oid]['malloc'] = uma_info[oid]['size'] * uma_info[oid]['stats.current']

    return uma_info

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
            value = parse_sysctl_value(line)
            memory_info[name] = value * pagesize

    return memory_info




if __name__ == '__main__':
    main()
