#!/usr/bin/env python
"""igcollect - Linux Load Average

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='load')
    return parser.parse_args()


def main():
    args = parse_args()
    with open('/proc/loadavg', 'r') as file_descriptor:
        avg01, avg05, avg15 = file_descriptor.readline().strip().split(' ')[:3]

    template = args.prefix + '.{} {} ' + str(int(time()))

    print(template.format('avg01', avg01))
    print(template.format('avg05', avg05))
    print(template.format('avg15', avg15))


if __name__ == '__main__':
    main()
