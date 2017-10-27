#!/usr/bin/env python
#
# igcollect - Redis keys
#
# Copyright (c) 2017 InnoGames GmbH
#

import redis
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='redis')
    parser.add_argument('--redis_host', default='localhost')
    parser.add_argument('--redis_port', default='6379')
    parser.add_argument('--command', default='llen')
    parser.add_argument('--keys', default='*queue*')
    return parser.parse_args()


def main():
    args = parse_args()

    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    redis_db = redis.StrictRedis(
        host=args.redis_host, port=args.redis_port, db=0)
    for key in redis_db.keys(args.keys):
        data = redis_db.execute_command(args.command, key)
        print(template.format(key, args.command, data))


if __name__ == '__main__':
    main()
