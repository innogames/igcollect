#!/usr/bin/env python
#
# igcollect - Memcached
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
import re
import telnetlib
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='memcached')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default='11211')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{} {} ' + str(int(time()))
    pattern = re.compile('STAT \w+ \d+(?:.\d+)?$')

    for line in command(args.host, args.port, 'stats').splitlines():
        if pattern.match(line):
            header, key, value = line.split()
            print(template.format(key, value))


def command(host, port, cmd):
    """Write a command to telnet and return the response"""
    client = telnetlib.Telnet(host, port)
    client.write(cmd + '\n')
    return client.read_until('END')


def is_float(value):
    try:
        float(value)
    except ValueError:
        return False
    else:
        return True


if __name__ == '__main__':
    main()
