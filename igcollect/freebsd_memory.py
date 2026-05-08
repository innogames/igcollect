#!/usr/bin/env python
"""igcollect - FreeBSD Memory Usage

Copyright (c) 2016 InnoGames GmbH
"""

from __future__ import print_function
from argparse import ArgumentParser
from time import time
import sysctl


# Translate sysctl to human-readable names in Grafana
MEMORY_TYPES = {
    'v_page_count': 'total',
    'v_free_count': 'free',
    'v_wire_count': 'wired',
    'v_user_wire_count': 'user_wired',
    'v_nofree_count': 'nofree',
    'v_active_count': 'active',
    'v_inactive_count': 'inactive',
    'v_laundry_count': 'laundry',
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='memory')
    return parser.parse_args()


def parse_memory_info():
    memory_info={}

    pagesize = sysctl.filter('vm.stats.vm.v_page_size')[0].value

    memory_data = sysctl.filter('vm.stats.vm')
    for line in memory_data:
        name = line.name.split('.')[-1]
        # After multiplying by page size they are not _count anymore
        memory_type = MEMORY_TYPES.get(name)
        if not memory_type:
            continue
        if name.endswith('_count'):
            if type(line.value) == bytearray:
                # py-sysctl lack support for CTLTYPE_U32
                # https://lists.freebsd.org/pipermail/freebsd-current/2018-July/070344.html
                value = int.from_bytes(line.value, byteorder='little', signed=False)
            else:
                value = line.value

            memory_info[memory_type] = value * pagesize

    return memory_info


def main():
    args = parse_args()

    template = args.prefix + '.{} {} ' + str(int(time()))
    for memory_name, memory_value in parse_memory_info().items():
        print(template.format(memory_name, memory_value))

if __name__ == '__main__':
    main()
