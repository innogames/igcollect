#!/usr/bin/env python
#
# igcollect - Redis
#
# Copyright (c) 2016 InnoGames GmbH
#


from argparse import ArgumentParser
from subprocess import Popen, PIPE
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='redis')
    return parser.parse_args()


def main():
    args = parse_args()
    redis_info = Popen(('redis-cli', '-a', redis_pwd(), 'info'),
                       stdout=PIPE).stdout.read()
    redis_info = redis_info.splitlines()

    redis_stats = {}
    for x in redis_info:
        if x.find(':') != -1:
            key, value = x.split(':')
            redis_stats[key] = value

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
