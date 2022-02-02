#!/usr/bin/env python3
"""Sentry stat collector

Copyright (c) 2022 InnoGames GmbH
"""
from argparse import ArgumentParser
from subprocess import run, PIPE, CalledProcessError
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='sentry.')
    parser.add_argument('--config_path', default='/etc/sentry/sentry.conf.py')
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        proc = run(
            ['sentry', '--config', f'{args.config_path}', 'queues', 'list'],
            universal_newlines=True,
            stdout=PIPE,
        )
        proc.check_returncode()
    except CalledProcessError as e:
        print(f'An exception occured: {e}')
        exit(1)

    for entry in proc.stdout.split('\n'):
        if len(entry.split(' ')) != 2:
            continue

        output = f'{args.prefix}{entry} {str(int(time()))}'
        print(output)


if __name__ == '__main__':
    main()
