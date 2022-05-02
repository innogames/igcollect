#!/usr/bin/env python
"""igcollect - Linux CPU Performance Factors

Copyright (c) 2020 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='cpu')
    return parser.parse_args()


def main():
    args = parse_args()
    factors = {
        'Intel(R) Xeon(R) CPU           L5520  @ 2.27GHz': 0.8,
        'Intel(R) Xeon(R) CPU           L5640  @ 2.27GHz': 1.0,
        'Intel(R) Xeon(R) CPU           X5650  @ 2.67GHz': 1.2,
        'Intel(R) Xeon(R) CPU E5-2407 0 @ 2.20GHz': 1.4,
        'Intel(R) Xeon(R) CPU E5-2660 0 @ 2.20GHz': 1.6,
        'Intel(R) Xeon(R) CPU E5-2660 v2 @ 2.20GHz': 1.65,
        'Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz': 1.85,
        'Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz': 1.75,
        'Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz': 1.8,
        'Intel(R) Xeon(R) Gold 6248 CPU @ 2.50GHz': 1.875,
        'AMD EPYC 7502P 32-Core Processor': 2.25,
        'AMD EPYC 7763 64-Core Processor': 2.25
    }
    cpufactor = 1.0

    with open('/proc/cpuinfo', 'r') as fp:
        for line in fp:
            if line.startswith('model name'):
                factor = line.split(':', 1)[1].strip()
                if factor in factors:
                    cpufactor = factors[factor]
                    break

    now = str(int(time()))
    print('{}.perffactor {} {}'.format(args.prefix, cpufactor, now))


if __name__ == '__main__':
    main()
