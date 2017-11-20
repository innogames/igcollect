#!/usr/bin/env python
#
# igcollect - Linux disk usage
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time
import os


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='fs')
    return parser.parse_args()


def main():
    args = parse_args()
    mountpoints = []
    with open('/proc/mounts', 'r') as fp:
        for line in fp:
            a, mountpoint, fstype, a = line.split(' ', 3)
            if fstype in ['ext2', 'ext3', 'ext4', 'xfs']:
                mountpoints.append(mountpoint)

    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    for mp in mountpoints:
        stat = os.statvfs(mp)
        used = stat.f_frsize * stat.f_blocks - stat.f_bfree * stat.f_bsize
        size = stat.f_frsize * stat.f_blocks

        if mp == '/':
            mp = 'rootfs'
        mp = mp.replace('/', '_').lstrip('_')

        print(template.format(mp, 'used', used))
        print(template.format(mp, 'size', size))


if __name__ == '__main__':
    main()
