#!/usr/bin/env python
#
# igcollect - Stats for Unbound DNS cache/resolver
#
# Copyright (c) 2019 InnoGames GmbH
#

from argparse import ArgumentParser
from subprocess import check_output
from time import time


def main():
    args = parse_args()
    template = args.prefix + '.{} {} ' + str(int(time()))
    for key, val in parse_unbound_stats().items():
        print(template.format(key, val))

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='unbound')
    return parser.parse_args()

def parse_unbound_stats():
    """ Get stas from unboud-control and split them into keys and values

        Output looks like this:
        thread0.num.queries=577686029
        total.num.queries=841735692

        We are not interested in per-thread stats, only total.
    """
    stats = check_output(
        ['/usr/local/sbin/unbound-control', 'stats'],
        universal_newlines=True,
        close_fds=False,
    ).split()

    out = {}
    for stat_k, stat_v in (x.split('=') for x in stats):
        # Report only stats for all threads
        if stat_k.startswith('total.'):
            # "total." is 6 char long
            stat_k = stat_k[6:].replace('.', '_')
            out[stat_k] = stat_v
    return out

if __name__ == '__main__':
    main()
