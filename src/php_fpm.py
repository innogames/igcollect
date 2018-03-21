#!/usr/bin/env python
#
# igcollect - PHP FPM
#
# This is the data collector for the PHP FPM status page.  It makes a
# HTTP request to get the page, and formats the output.  All the numeric
# values of the requested pool is printed.
#
# Copyright (c) 2018, InnoGames GmbH
#

from time import time
from argparse import ArgumentParser

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='php_fpm')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--address')
    parser.add_argument('--location', default='/fpm-status')
    parser.add_argument('--pool', default='www')
    return parser.parse_args()


def main():
    args = parse_args()
    url = 'http://' + (args.address or args.host) + args.location
    request = Request(url, headers={'Host': args.host})
    response = urlopen(request)

    template = args.prefix + '.{} {} ' + str(int(time()))
    pool_found = False
    for line in response.readlines():
        key, value = line.split(':', 1)
        key = key.replace(' ', '_')
        value = value.strip()

        if key == 'pool':
            pool_found = value == args.pool

        if pool_found and value.isdigit():
            print(template.format(key, value.strip()))


if __name__ == '__main__':
    main()
