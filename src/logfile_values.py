#!/usr/bin/env python
#
# logfile_values.py
#
# Copyright (c) 2017, InnoGames GmbH
#
"""
logfile_values.py -- a python script to find metrics values in log file

This script is using last line of log file to get metric value by column number

python logfile_values.py --metric="metric1:1" --metric="metric2:2" ...
"""

from argparse import ArgumentParser, ArgumentTypeError
from time import time


class Metric:
    def __init__(self, arg):
        if ':' not in arg:
            raise ArgumentTypeError('Argument must have ":"')
        self.name, column = arg.split(':', 1)
        if not column.isdecimal():
            raise ArgumentTypeError('Column must be a number')
        self.column = int(column)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='logfile_values')
    parser.add_argument('--file', default='/var/log/messages')
    parser.add_argument('--metric', type=Metric, action='append')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{} {} ' + str(int(time()))
    with open(args.file, 'r') as f:
        for line in f:
            pass
        last_line = line.split()
    for m in args.metric:
        print(template.format(m.name, last_line[m.column]))


if __name__ == '__main__':
    main()
