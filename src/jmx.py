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
    parser.add_argument('--port', required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    p = Popen(['java', '-jar', '/usr/share/igcollect/libigcollect/jmxcollect.jar', '--host', 'localhost', '--prefix', args.prefix, '--port', args.port], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()

    print(output)
    exit(p.returncode)

if __name__ == '__main__':
    main()
