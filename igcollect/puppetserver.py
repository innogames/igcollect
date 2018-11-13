#!/usr/bin/env python
"""igcollect - Puppetserver

Copyright (c) 2018 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time
from urllib.request import urlopen

import json
import ssl
import re


def parse_args():
    """CLI"""
    parser = ArgumentParser()
    parser.add_argument('-p', '--prefix', default='puppetserver')
    parser.add_argument('--host', default='localhost:8140')
    parser.add_argument('--with-profiler', action='store_true')
    parser.add_argument('--no-ssl-verify', action='store_true')
    parser.add_argument('-c', '--cert')
    parser.add_argument('-k', '--key')
    parser.add_argument('-a', '--cacert')

    return parser.parse_args()


def main():
    """Request puppetserver metrics API and print out in a format that can
    directly be sent out to graphite.
    """
    args = parse_args()
    data = fetch_metrics(args.host, args.no_ssl_verify, args.cert, args.key,
                         args.cacert)
    collect_metrics(data, args.prefix, args.with_profiler)


def fetch_metrics(host, no_ssl_verify=False, cert=None, key=None, cacert=None):
    """Fetches the metrics from the puppetserver API"""
    # TLS
    ctxt = ssl.create_default_context()
    if no_ssl_verify:
        ctxt.check_hostname = False
        ctxt.verify_mode = ssl.CERT_NONE
    elif cert and key and cacert:
        ctxt.verify_mode = ssl.CERT_REQUIRED
        ctxt.load_cert_chain(cert, key)
        ctxt.load_verify_locations(cacert)

    # Request metrics api
    url = 'https://{}/status/v1/services?level=debug'.format(host)
    response = urlopen(url, context=ctxt)

    return json.loads(response.read().decode('utf-8'))


def collect_metrics(data, prefix, with_profiler=False):
    """Parses and prints out fetched metrics"""
    template = prefix + '.{} {} ' + str(int(time()))

    # Collect HTTP metrics
    http = data['master']['status']['experimental']
    descs = {'http-metrics': ['route-id', 'mean']}
    print_metrics(template, descs, http)

    # Collect JRuby metrics
    jruby = data['jruby-metrics']['status']['experimental']['metrics']
    for metric in jruby:
        if isinstance(jruby[metric], list):
            for val in jruby[metric]:
                print_single(template, 'jruby-metrics', metric, val)

            continue

        print_single(template, 'jruby-metrics', metric, jruby[metric])

    # Skip profiler metrics if not requested
    if not with_profiler:
        return

    # Collect profiler metrics
    profiler = data['puppet-profiler']['status']['experimental']
    descs = {
        'function-metrics': ['function', 'mean'],
        'resource-metrics': ['resource', 'mean'],
        'catalog-metrics': ['metric', 'mean'],
        'inline-metrics': ['metric', 'count'],
    }
    print_metrics(template, descs, profiler)


def print_metrics(template, descs, data):
    """Print a metrics tree from the API"""
    for name, paths in descs.items():
        key, metric_key = paths

        for metric in data[name]:
            print_single(template, name, metric[key], metric[metric_key])


def print_single(template, prefix, subpath, value):
    """Sanitize and print a single metric"""
    # Replace all non-alphanumeric characters with underscores to not dump
    # garbage into graphite
    pattern = re.compile('[^a-zA-Z\d]')
    path = '{}.{}'.format(prefix, re.sub(pattern, '_', subpath).rstrip('_'))

    print(template.format(path, value))


if __name__ == '__main__':
    main()
