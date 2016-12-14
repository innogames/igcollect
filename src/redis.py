#!/usr/bin/env python
#
# igcollect - Redis
#
# Copyright (c) 2016 InnoGames GmbH
#

import socket, time, subprocess

def main():
    redis_info = subprocess.Popen(('redis-cli', '-a', redis_pwd(), 'info'),
                                  stdout=subprocess.PIPE).stdout.read()
    redis_info = redis_info.splitlines()

    redis_stats = {}
    for x in redis_info:
        if x.find(':') != -1:
            key, value = x.split(':')
            redis_stats[key] = value

    hostname = socket.gethostname().replace('.', '_')
    timestamp = str(int(time.time()))
    template = 'servers.' + hostname + '.software.redis.{1} {2} ' + timestamp
    headers = (
            'total_connections_received',
            'total_commands_processed',
            'keyspace_hits',
            'keyspace_misses',
            'used_memory',
        )

    for metric in headers:
        print(template.format(hostname,metric, redis_stats[metric]))

def redis_pwd():
    '''Returns redis password '''
    with open("/etc/redis/redis.conf") as f:
        secret_cfg = f.read().split("\n")

    for line in secret_cfg:
        line = line.strip()
        if line.startswith("requirepass"):
            return line.split(" ")[1].strip()
    return ''

if __name__ == '__main__':
    main()
