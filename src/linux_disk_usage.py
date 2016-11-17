#!/usr/bin/env python
#
# igcollect - Linux disk usage
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import socket
import time
import os


def main():
    mountpoints = []
    with open('/proc/mounts', 'r') as file_descriptor:
        for line in file_descriptor.readlines():
            a, mountpoint, fstype, a = line.split(' ', 3)
            if fstype in ['ext2', 'ext3', 'ext4', 'xfs']:
                mountpoints.append(mountpoint)

    now = str(int(time.time()))
    hostname = socket.gethostname().replace('.', '_')

    template = 'servers.' + hostname + '.system.fs.{}.{} {} ' + now

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
