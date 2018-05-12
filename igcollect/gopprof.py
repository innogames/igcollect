#!/usr/bin/env python
"""igcollect - GO pprof

Copyright (c) 2017 InnoGames GmbH
"""

from argparse import ArgumentParser
from os.path import dirname, abspath
from subprocess import Popen, PIPE
from sys import exit
from time import time
try:
    from subprocess import DEVNULL # py3
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='pprof')
    parser.add_argument('--pprof', default='/usr/local/go/bin/go tool pprof', help='Path to go pprof')
    parser.add_argument('--ports', default=[], nargs='+')
    parser.add_argument('--names', default=[], nargs='+')
    return parser.parse_args()


def get_cpu_profile(pprof_path, replace_symbols, url):
    profile = Popen(pprof_path.split() + [
        '-seconds', '30',
        '-top',
        url + '/profile'
    ], env=dict(os.environ, PPROF_TMPDIR='/dev/null'), stdout=PIPE, stderr=DEVNULL).stdout.read()

    profile_list = profile.splitlines()
    profile_list = profile_list[2:]

    return_list = {}
    for line in profile_list:
         split = line.split()
         metric_name = split[5]
         for was, now in replace_symbols.items():
             metric_name = metric_name.replace(was, now, -1)

         flat = split[0].strip('ms')
         if flat == '0':
             break
         return_list[metric_name] = flat

    return return_list


def get_mem_heap(pprof_path, replace_symbols, url):
    heap = Popen(pprof_path.split() + [
        '-unit', 'B',
        '-top',
       url + '/heap'
    ], env=dict(os.environ, PPROF_TMPDIR='/dev/null'), stdout=PIPE, stderr=DEVNULL).stdout.read()

    heap_list = heap.splitlines()
    heap_list = heap_list[3:]

    return_list = {}
    for line in heap_list:
         split = line.split()
         metric_name = split[5]
         for was, now in replace_symbols.items():
             metric_name = metric_name.replace(was, now, -1)

         flat = split[0].strip('B')
         if flat == '0':
            break
         # The value should be in bytes
         return_list[metric_name] = flat

    return return_list


def main():
    args = parse_args()
    if len(args.ports) != len(args.names):
        print('Length of ports must be the same as length of names')
        exit(1)

    # list of symbols to replace for graphite compatibility
    replace_symbols = {'*': '', '.': '_', '/': '_', '(': '_', ')': '_'}

    template = args.prefix + '.{} {} ' + str(int(time()))

    for index, name in enumerate(args.names):
        base_url = 'http://localhost:'+ args.ports[index] + '/debug/pprof'
        for mname, mvalue in get_cpu_profile(args.pprof, replace_symbols, base_url).items():
            print(template.format(name + '.profile.flat.' + mname, mvalue))

        for mname, mvalue in get_mem_heap(args.pprof, replace_symbols, base_url).items():
            print(template.format(name + '.heap.flat.' + mname, mvalue))



if __name__ == '__main__':
    main()
