#!/usr/bin/env python
#
# igcollect - FreeBSD cpu usage
#
# Copyright (c) 2016 InnoGames GmbH
#

from __future__ import print_function
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from time import time

# CPU usage is taken from kern.cp_times sysctl.
# The result is a single row with numbers. Each 5 numbers form stats of one CPU.
# Order is: user nice sys interrupt idle

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='cpu')
    return parser.parse_args()


def parse_cpu_stats():
    cpu_stats={}
    cpu_times = Popen(('/sbin/sysctl', 'kern.cp_times'), stdout=PIPE).\
               stdout.read().split(':')[1].split()

    cpu = 0
    cpus = len(cpu_times)/5
    while cpu < cpus:
        cpu_stats[cpu] = (cpu_times[cpu*5:(cpu+1)*5])
        cpu += 1
    return cpu_stats


def main():
    args = parse_args()

    # Add extra 0 to CPU number for nice sorting in Grafana.
    template = args.prefix + '.{:02d}.{} {} ' + str(int(time()))

    for index, cnt in parse_cpu_stats().iteritems():
        print(template.format(index, 'user', cnt[0]))
        print(template.format(index, 'nice', cnt[1]))
        print(template.format(index, 'system', cnt[2]))
        print(template.format(index, 'irq', cnt[3]))
        print(template.format(index, 'idle', cnt[4]))


if __name__ == '__main__':
    main()
