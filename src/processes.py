#!/usr/bin/env python
#
# igcollect - process stat
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from subprocess import check_output
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='processes')
    parser.add_argument('--commands', default=[], nargs='*')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    for command in args.commands:
        cpu, mem = get_process_data(command)
        print(template.format(command, 'cpu_usage', cpu))
        print(template.format(command, 'mem_usage', mem))


def get_process_data(command):
    pid = check_output(('pgrep', '-f', command)).strip()
    process_data = check_output(('ps', '-p', pid, '-o', 'pcpu=,pmem=')).strip()
    return process_data.split()


if __name__ == '__main__':
    main()
