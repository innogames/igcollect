#!/usr/bin/env python
#
# igcollect - JVM stat
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time
from subprocess import Popen, PIPE
import os


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='jmx')
    parser.add_argument('--ports', default=[], nargs='+')
    parser.add_argument('--names', default=[], nargs='+')
    return parser.parse_args()


def main():
    args = parse_args()

    if len(args.ports) != len(args.names):
        print("Length of ports must be the same as length of names")
        exit(1)

    exit_code = 0
    for index, name in enumerate(args.names):
        p = Popen(['java', '-jar', '/usr/share/igcollect/libigcollect/jmxcollect.jar', '--host', 'localhost', '--prefix', args.prefix + '.' + name, '--port', args.ports[index]], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        print(output)
        if p.returncode > exit_code:
            exit_code = p.returncode

    exit(exit_code)


if __name__ == '__main__':
    main()
