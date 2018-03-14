#!/usr/bin/env python
#
# igcollect - Nginx
#
# Copyright (c) 2018, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='nginx')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--url', default='http://localhost/nginx_status')
    return parser.parse_args()


def main():
    args = parse_args()
    stub_status = {}

    # Get information from stub_status page
    headers = {'Host': args.host}
    response = urlopen(Request(args.url, headers=headers))
    s = response.read().splitlines()
    # Current active connections
    stub_status['active_connections'] = s[0].split(b':')[1].strip()
    # All accepted connections since server restart
    stub_status['accepted_connections'] = s[2].split()[0].strip()
    # All connections that were processed
    stub_status['handled_connections'] = s[2].split()[1].strip()
    # All requests which were processed
    stub_status['handled_requests'] = s[2].split()[2].strip()
    # Current reading connections, reads request header
    stub_status['reading'] = s[3].split()[1].strip()
    # Current writing connections, reads request body, processes request, or
    # writes response to a client
    stub_status['writing'] = s[3].split()[3].strip()
    # Keep-alive connections, actually it is active - (reading + writing
    stub_status['waiting'] = s[3].split()[5].strip()

    template = args.prefix + '.stub_status.{0} {1} ' + str(int(time()))
    for key, value in stub_status.items():
        print(template.format(key, value.decode('utf-8')))


if __name__ == '__main__':
    main()
