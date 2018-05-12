#!/usr/bin/env python
"""igcollect - Redis

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from subprocess import check_output
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='redis')
    return parser.parse_args()


def main():
    args = parse_args()
    redis_info = check_output(['redis-cli', '-a', redis_pwd(), 'info'])

    redis_stats = {}
    for x in redis_info.splitlines():
        if x.find(b':') != -1:
            key, value = x.split(b':')
            redis_stats[key.decode('utf-8')] = value.decode('utf-8')

    template = args.prefix + '.{} {} ' + str(int(time()))
    headers = (
        'total_connections_received',
        'total_commands_processed',
        'keyspace_hits',
        'keyspace_misses',
        'used_memory',
        'used_cpu_sys',
        'used_cpu_user',
        'used_cpu_sys_children',
        'used_cpu_user_children',
    )
    for metric in headers:
        print(template.format(metric, redis_stats[metric]))


def redis_pwd():
    """Get the Redis password from the configuration"""
    with open("/etc/redis/redis.conf") as fd:
        secret_cfg = fd.read().splitlines()

    for line in secret_cfg:
        line = line.strip()
        if line.startswith("requirepass"):
            return line.split(" ")[1].strip()
    return ''


if __name__ == '__main__':
    main()
