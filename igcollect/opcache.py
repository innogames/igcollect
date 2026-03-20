#!/usr/bin/env python3
"""igcollect - PHP OPcache

Collects memory usage metrics from PHP OPcache via a status endpoint
that returns opcache_get_status() as JSON.

Copyright (c) 2026 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time
import json
import urllib.request
import ssl


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='opcache')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--location', default='/opcache.php?action=stats')
    return parser.parse_args()


def main():
    args = parse_args()
    url = 'https://' + args.host + args.location

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(url, context=ctx) as response:
        stats = json.loads(response.read())

    now = int(time())
    template = args.prefix + '.{} {} ' + str(now)

    memory = stats['memory_usage']
    print(template.format('memory.used', memory['used_memory']))
    print(template.format('memory.free', memory['free_memory']))

    interned = stats['interned_strings_usage']
    print(template.format('interned_strings.used', interned['used_memory']))
    print(template.format('interned_strings.free', interned['buffer_size'] - interned['used_memory']))

    opcache_stats = stats['opcache_statistics']
    print(template.format('statistics.hit_rate', opcache_stats['opcache_hit_rate']))
    print(template.format('statistics.hits', opcache_stats['hits']))
    print(template.format('statistics.misses', opcache_stats['misses']))
    print(template.format('statistics.num_cached_scripts', opcache_stats['num_cached_scripts']))

    preload = stats.get('preload_statistics')
    if preload:
        print(template.format('preload.memory_consumption', preload['memory_consumption']))
        for key in ('scripts', 'functions', 'classes'):
            if key in preload:
                print(template.format(f'preload.num_{key}', len(preload[key])))


if __name__ == '__main__':
    main()
