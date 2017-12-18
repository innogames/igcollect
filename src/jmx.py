#!/usr/bin/env python
#
# igcollect - JVM stat
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from os.path import dirname, abspath
from subprocess import Popen
from sys import exit


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='jmx')
    parser.add_argument('--ports', default=[], nargs='+')
    parser.add_argument('--names', default=[], nargs='+')
    parser.add_argument('--thread-prefixes', default=[], nargs='+')
    return parser.parse_args()


def main():
    args = parse_args()
    jar_path = dirname(abspath(__file__)) + '/../../share/java/jmxcollect.jar'
    thread_prefixes = ','.join(args.thread_prefixes)

    if len(args.ports) != len(args.names):
        print('Length of ports must be the same as length of names')
        exit(1)

    exit_code = 0
    for name, port in zip(args.names, args.ports):
        proc = Popen([
            'java',
            '-jar',
            jar_path,
            '--host',
            'localhost',
            '--prefix',
            args.prefix + '.' + name,
            '--port',
            port,
            '--thread-prefixes',
            thread_prefixes,
        ])
        exit_code = max(proc.wait(), exit_code)

    exit(exit_code)


if __name__ == '__main__':
    main()
