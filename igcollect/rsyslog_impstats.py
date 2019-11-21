#!/usr/bin/env python3
'''igcollect - Rsyslog impstats log parser

Copyright (c) 2019 InnoGames GmbH
'''

import re
from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='rsyslog')
    parser.add_argument('--filename', default='/var/log/pstats')
    parser.add_argument(
        '--stats', nargs='+',
        choices=['size', 'enqueued', 'discarded_full'],
        default=['size', 'enqueued', 'discarded_full']
    )
    return parser.parse_args()


def main():
    args = parse_args()
    stats = parse_log(args.filename)

    used_fields = set(args.stats)

    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    for action, stat in stats.items():
        for field in used_fields:
            print(template.format(action, field, stat[field]))


def parse_log(filename):
    actions = {}

    with open(filename) as pstats_file:
        # Nov 5 00:00:00 localhost rsyslogd-pstats: action-3-builtin:omfwd:\
        #  queue: origin=core.queue size=0 enqueued=176432440 full=0\
        #  discarded.full=0 discarded.nf=0 maxqsize=92057
        regex = re.compile(
            r'(?P<action>action-\d+).* queue(?P<is_DA>\[DA\]|)'
            r': .*size=(?P<size>\d+) enqueued=(?P<enqueued>\d+)'
            r' .* discarded\.full=(?P<discarded_full>\d+)'
        )
        for line in pstats_file:
            match = regex.search(line)
            if not match:
                continue

            stats = match.groupdict()
            action_name = stats.pop('action').replace('-', '')
            is_DA = bool(stats.pop('is_DA'))

            # If we use disk assisted queues, we want those stats as well
            if is_DA:
                actions[action_name + '_DA'] = stats
            else:
                actions[action_name] = stats
    return actions


if __name__ == '__main__':
    main()
