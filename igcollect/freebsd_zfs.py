#!/usr/bin/env python3

"""igcollect - ZFS on FreeBSD

Copyright © 2023 InnoGames GmbH
"""

from argparse import ArgumentParser

from subprocess import check_output
from time import time


# Convert to names already used at IG:
ZPOOL_SIZE_COLUMNS = (
    ('name', None), # Translated to result dict key
    ('size', 'size'),
    ('allocated', 'used'),
    ('fragmentation', 'fragmentation'),
)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='disk')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    zfs_usage = get_zfs_usage()
    for zpool_name, zpool_stats in zfs_usage.items():
        for stat_name, stat_value in zpool_stats.items():
            print(template.format(zpool_name, stat_name, stat_value))


def get_zfs_usage():
    ret = {}

    out = check_output(['zpool', 'list',
        '-H', '-p',
        '-o', 'name,size,allocated,fragmentation'],
       universal_newlines=True,
    )

    for line in out.splitlines():
        columns = line.split()
        ret[columns[0]] = {}
        # Column 0 is the key, the further ones are stored in the value.
        for col_idx in range(1,len(ZPOOL_SIZE_COLUMNS)):
            ret[columns[0]][ZPOOL_SIZE_COLUMNS[col_idx][1]] = columns[col_idx]

    return ret


if __name__ == '__main__':
    main()
