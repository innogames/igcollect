#!/usr/bin/env python3
"""igcollect - Kea DHCP

Copyright (c) 2026 InnoGames GmbH
"""

import json
import re
import socket
from argparse import ArgumentParser, Namespace
from time import time
from urllib.request import Request, urlopen


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='kea')
    parser.add_argument('--host')
    parser.add_argument('--port', type=int, help='Kea DHCP server HTTP port')
    parser.add_argument('--socket', dest='socket_path',
                        help='Path to the Kea control unix socket')

    args = parser.parse_args()

    if not args.socket_path and not (args.host and args.port):
        parser.error('you must provide either --socket or both --host and --port')

    if args.socket_path and (args.host or args.port):
        parser.error('--socket cannot be used together with --host/--port')

    if bool(args.host) != bool(args.port):
        parser.error('--host and --port must be used together')

    return args


def main() -> None:
    args = parse_args()
    timestamp = int(time())

    stats = get_stats(args)
    for name, samples in stats.items():
        value = samples[0][0]
        print(f'{args.prefix}.{sanitize_metric(name)} {value} {timestamp}')


def get_stats(args: Namespace) -> dict:
    payload = json.dumps({
        'command': 'statistic-get-all',
    }).encode()

    if args.socket_path:
        body = query_unix(args.socket_path, payload)
    else:
        body = query_http(args.host, args.port, payload)
    result = json.loads(body)

    # Kea supports sending commands for multiple services together, but we don't do it.
    # As a consequence, the responses are wrapped in a list with a single member.
    if isinstance(result, list):
        result = result[0]

    if result.get('result') != 0:
        raise RuntimeError(f"Kea returned error: {result.get('text', 'unknown')}")

    return result['arguments']


def query_unix(socket_path: str, payload: bytes) -> str:
    """Send a command over a Kea control unix socket.

    The control channel exposed directly by kea-dhcp4/kea-dhcp6 speaks raw
    JSON with no HTTP framing: write the command, read the response.
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect(socket_path)
        sock.sendall(payload)
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    return b''.join(chunks).decode('utf-8')


def query_http(host: str, port: int, payload: bytes) -> str:
    # We should enclose IPv6 literals in square brackets
    if ':' in host:
        host = f'[{host}]'

    req = Request(
        f'http://{host}:{port}/',
        data=payload,
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(req, timeout=10) as response:
        body = response.read().decode('utf-8')
        return body


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
