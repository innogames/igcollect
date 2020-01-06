#!/usr/bin/env python
"""igcollect - JSON via HTTP

Copyright (c) 2018 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time
from urllib.request import urlopen

import json


def parse_args():
    parser = ArgumentParser(usage=(
        'python3 igcollect/url_json.py'
        ' --prefix servers.HOSTNAME.software.uwsgi'
        ' --url http://localhost:8080'
        ' --key pid'
        ' --json-path workers.[*].requests workers.[*].respawn_count'
    ), description=(
        'Query JSON from URL and extract metrics for graphite text protocol'
    ))
    parser.add_argument('--prefix', default='url_json')
    parser.add_argument('--url', default='http://localhost/')
    parser.add_argument(
        '--key',
        nargs='+',
        dest='keys',
        help='Plain string to match JSON key e.g.: workers.requests',
    )
    parser.add_argument(
        '--json-path',
        nargs='+',
        dest='jsonpaths',
        help=(
            'JSON path to match key e.g.: workers[*].requests '
            '(requires: jsonpath-rw module)')
    )
    return parser.parse_args()


def main():
    args = parse_args()
    response = urlopen(args.url)
    data = json.loads(response.read().decode('utf-8'))

    template = args.prefix + '.{} {} ' + str(int(time()))

    if args.keys:
        for key, value in data.items():
            if key in args.keys:
                print(template.format(key, value))

    if args.jsonpaths:
        from jsonpath_rw import parse

        for path in args.jsonpaths:
            for match in parse(path).find(data):
                # Graphite text protocol can not process square brackets
                graphite_path = str(match.full_path).replace('[', '').replace(
                    ']', '')
                print(template.format(graphite_path, match.value))


if __name__ == '__main__':
    main()
