#!/usr/bin/env python
#
# igcollect - FreeBSD memory usage
#
# Copyright (c) 2016 InnoGames GmbH
#

from __future__ import print_function
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='memory_usage')
    return parser.parse_args()


def parse_memory_info():
    memory_info={}

    memory_data = Popen(('/sbin/sysctl', 'hw.physmem'), stdout=PIPE).\
                  stdout.read()
    memory_info['physmem'] = int(memory_data.split(':')[1])

    # All other data is reported in pages
    memory_data = Popen(('/sbin/sysctl', 'hw.pagesize'), stdout=PIPE).\
                  stdout.read()
    pagesize = int(memory_data.split(':')[1])

    memory_data = Popen(('/sbin/sysctl', 'vm.stats.vm'), stdout=PIPE).\
               stdout.read().splitlines()
    for line in memory_data:
        line = line.split(':')
        name = line[0].split('.')[3]
        # After multiplying by page size they are not _count anymore
        if name.endswith('_count'):
            name = name.replace('_count', '')
            memory_info[name] = int(line[1]) * pagesize

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
