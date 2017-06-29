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
    return parser.parse_args()


def main():
    args = parse_args()
    jar_path = dirname(abspath(__file__)) + '/../../share/java/jmxcollect.jar'

    if len(args.ports) != len(args.names):
        print('Length of ports must be the same as length of names')
        exit(1)

    exit_code = 0
    for index, name in enumerate(args.names):
        proc = Popen([
            'java',
            '-jar',
            jar_path,
            '--host',
            'localhost',
            '--prefix',
            args.prefix + '.' + name,
            '--port',
            args.ports[index],
        ])
        if proc.wait() > exit_code:
            exit_code = proc.returncode

    exit(exit_code)


if __name__ == '__main__':
    main()
