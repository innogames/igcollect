#!/usr/bin/env python3
"""igcollect - Kea DHCP

Copyright (c) 2026 InnoGames GmbH
"""

import json
import re
from argparse import ArgumentParser, Namespace
from time import time
from urllib.request import Request, urlopen


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='kea')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=8000,
                        help='Kea DHCP server HTTP port (default: 8000)')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = int(time())

    stats = get_stats(args.host, args.port)
    for name, samples in stats.items():
        value = samples[0][0]
        print(f'{args.prefix}.{sanitize_metric(name)} {value} {timestamp}')


def get_stats(host: str, port: int) -> dict:
    payload = json.dumps({
        'command': 'statistic-get-all',
    }).encode()
    req = Request(
        f'http://{host}:{port}/',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(req, timeout=10) as response:
        body = response.read().decode('utf-8')
        result = json.loads(body)

    # Kea supports sending commands for multiple services together, but we don't do it.
    # As a consequence, the responses are wrapped in a list with a single member.
    if isinstance(result, list):
        result = result[0]

    if result.get('result') != 0:
        raise RuntimeError(f"Kea returned error: {result.get('text', 'unknown')}")

    return result['arguments']


def sanitize_metric(name: str) -> str:
    """Convert a Kea stat name to a Graphite-compatible metric path.

    Examples:
        pkt4-received               -> pkt4_received
        subnet[1].assigned-addresses -> subnet.1.assigned_addresses
        subnet[1].pool[0].total-addresses -> subnet.1.pool.0.total_addresses
        subnet[1].pd-pool[0].total-pds    -> subnet.1.pd_pool.0.total_pds
    """
    name = re.sub(r'\[(\d+)\]', r'.\1', name)
    name = name.replace('-', '_')
    return name


if __name__ == '__main__':
    main()
