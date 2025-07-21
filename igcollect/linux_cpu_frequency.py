#!/usr/bin/env python
"""igcollect - Linux CPU Frequency

Copyright (c) 2025 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time

import os

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='cpufreq')
    return parser.parse_args()

def main():
    args = parse_args()
    now = str(int(time()))
    header = (
        'frequency',
    )
    cs = get_cpufreq_dict()
    for cpu in cs:
        for metric in header:
            print(
                '{}.{}.{} {} {}'
                .format(args.prefix, cpu, metric, cs[cpu][metric], now)
            )

def get_cpufreq_dict():
    cpufreq_dict = {}
    cpu_path = '/sys/devices/system/cpu/'
    for entry in os.listdir(cpu_path):
        if entry.startswith('cpu') and entry[3:].isdigit():
            cpu_num = entry[3:]
            freq_file = os.path.join(cpu_path, entry, 'cpufreq', 'scaling_cur_freq')
            try:
                with open(freq_file, 'r') as f:
                    freq = int(f.read().strip())
            except Exception:
                freq = 0
            cpufreq_dict[cpu_num] = {'frequency': freq}
    return cpufreq_dict

if __name__ == '__main__':
    main()
