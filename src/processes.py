#!/usr/bin/env python
"""igcollect - OS Processes

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from collections import namedtuple
from re import compile
from subprocess import check_output
from time import time
from platform import system


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='processes')
    parser.add_argument('--commands', default=[], nargs='*')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    processes = list(get_processes())
    for command in args.commands:
        pattern = compile(command)

        for process in processes:
            if pattern.search(process.command):
                print(template.format(command, 'cpu_usage', process.pcpu))
                print(template.format(command, 'mem_usage', process.pmem))
                print(template.format(command, 'etimes', process.etimes))
                print(template.format(command, 'rss', int(process.rss) * 1024))
                break


def get_processes():
    columns = ['pcpu', 'pmem', 'etimes', 'rss', 'command']
    Process = namedtuple('Process', columns)
    if system() == 'Linux':
        args = ['ps', '-A', '--sort=start_time'] + ['-o' + c for c in columns]
    else:
        args = ['ps', '-A', '-O started'] + ['-o' + c for c in columns]
    for line in check_output(args).decode('utf-8').splitlines():
        yield Process(*line.strip().split(None, len(columns) - 1))


if __name__ == '__main__':
    main()
