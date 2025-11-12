#!/usr/bin/env python3
"""igcollect - Redis

Copyright (c) 2025 InnoGames GmbH
"""

from argparse import ArgumentParser, Namespace
from subprocess import check_output
from time import time


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='redis')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = get_redis_conf('requirepass', 'port')

    cli_command = ['redis-cli']
    if 'requirepass' in cfg:
        cli_command.extend(['-a', cfg['requirepass']])
    if 'port' in cfg:
        cli_command.extend(['-p', cfg['port']])
    cli_command.append('info')
    redis_info = check_output(cli_command, text=True)

    redis_stats = {}
    for line in redis_info.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            redis_stats[key] = value

    timestamp = int(time())
    headers = (
        # Clients
        'blocked_clients',
        'connected_clients',

        # CPU
        'used_cpu_sys',
        'used_cpu_user',
        'used_cpu_sys_children',
        'used_cpu_user_children',

        # Memory
        'mem_fragmentation_ratio',
        'mem_replication_backlog',
        'used_memory',

        # Stats
        'evicted_keys',
        'keyspace_hits',
        'keyspace_misses',
        'total_connections_received',
        'total_commands_processed',
    )
    for metric in headers:
        print(f'{args.prefix}.{metric} {redis_stats.get(metric)} {timestamp}')


def get_redis_conf(*args) -> dict[str, str]:
    """Get requested parameters from the configuration"""
    with open("/etc/redis/redis.conf") as fd:
        content = fd.read().splitlines()

    cfg = {}
    for line in content:
        parts = line.split()
        if not parts:
            continue

        if parts[0] not in args:
            continue

        cfg[parts[0]] = parts[1]

    return cfg


if __name__ == '__main__':
    main()
