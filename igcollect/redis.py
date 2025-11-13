#!/usr/bin/env python3
"""igcollect - Redis

Copyright (c) 2025 InnoGames GmbH
"""

from argparse import ArgumentParser, Namespace
from subprocess import check_output, DEVNULL
from time import time


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='redis')
    parser.add_argument('--latencystats', action='store_true', default=False,
                        help='Collect latency statistics')
    parser.add_argument('--commandstats', action='store_true', default=False,
                        help='Collect command statistics')
    parser.add_argument('--reset-stats', action='store_true', default=False,
                        help='Reset statistics after collection')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = get_redis_conf('requirepass', 'port')
    timestamp = int(time())

    # Collect standard redis info
    redis_info = run_redis_cli(cfg, 'info')
    redis_stats = {}
    for line in redis_info.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            redis_stats[key] = value

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

    # Collect commandstats if requested
    if args.commandstats:
        commandstats_info = run_redis_cli(cfg, 'INFO COMMANDSTATS')
        commandstats = parse_commandstats(commandstats_info)
        for cmd_name, cmd_stats in commandstats.items():
            # Replace pipe with underscore for graphite compatibility
            cmd_name = cmd_name.replace('|', '_')
            for stat_name, stat_value in cmd_stats.items():
                print(f'{args.prefix}.commandstats.{cmd_name}.{stat_name} {stat_value} {timestamp}')

    # Collect latencystats if requested
    if args.latencystats:
        latencystats_info = run_redis_cli(cfg, 'INFO LATENCYSTATS')
        latencystats = parse_latencystats(latencystats_info)

        for cmd_name, cmd_stats in latencystats.items():
            # Replace pipe with underscore for graphite compatibility
            cmd_name = cmd_name.replace('|', '_')
            for percentile, value in cmd_stats.items():
                # Replace dots in percentile names (e.g., p99.9 -> p99_9)
                percentile = percentile.replace('.', '_')
                print(f'{args.prefix}.latencystats.{cmd_name}.{percentile} {value} {timestamp}')

    # Reset stats if requested (after collection)
    if args.reset_stats:
        run_redis_cli(cfg, 'CONFIG RESETSTAT')


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


def parse_commandstats(info_output: str) -> dict[str, dict[str, str]]:
    """Parse commandstats info output into a structured format"""
    stats = {}
    for line in info_output.splitlines():
        if line.startswith('cmdstat_'):
            # Format: cmdstat_command:calls=X,usec=Y,usec_per_call=Z,rejected_calls=A,failed_calls=B
            cmd_name, values = line.split(':', 1)
            cmd_name = cmd_name.replace('cmdstat_', '')

            cmd_stats = {}
            for pair in values.split(','):
                key, value = pair.split('=', 1)
                cmd_stats[key] = value

            stats[cmd_name] = cmd_stats

    return stats


def parse_latencystats(info_output: str) -> dict[str, dict[str, str]]:
    """Parse latencystats info output into a structured format"""
    stats = {}
    for line in info_output.splitlines():
        if line.startswith('latency_percentiles_usec_'):
            # Format: latency_percentiles_usec_command:p50=X,p99=Y,p99.9=Z
            cmd_name, values = line.split(':', 1)
            cmd_name = cmd_name.replace('latency_percentiles_usec_', '')

            cmd_stats = {}
            for pair in values.split(','):
                key, value = pair.split('=', 1)
                cmd_stats[key] = value

            stats[cmd_name] = cmd_stats

    return stats


def run_redis_cli(cfg: dict[str, str], command: str) -> str:
    """Execute a redis-cli command and return the output"""
    cli_command = ['redis-cli']
    if 'requirepass' in cfg:
        cli_command.extend(['-a', cfg['requirepass']])
    if 'port' in cfg:
        cli_command.extend(['-p', cfg['port']])
    cli_command.extend(command.split())
    return check_output(cli_command, text=True, stderr=DEVNULL)


if __name__ == '__main__':
    main()
