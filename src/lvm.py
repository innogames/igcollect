#!/usr/bin/env python
#
# igcollect - Linux volume manager
#
# Copyright (c) 2016, InnoGames GmbH
#

from socket import gethostname
import time
import sys
import subprocess


def main():
    try:
        vgdisplay = subprocess.Popen(
            '/sbin/vgdisplay -c',
            stdout=subprocess.PIPE,
            shell=True,
            stdin=subprocess.PIPE,
            close_fds=True,
        ).stdout.readlines()
    except:
        sys.exit(1)

    template = 'servers.{}.system.lvm.{}.{} {} {}'
    hostname = gethostname().replace('.', '_')
    timestamp = str(int(time.time()))

    for line in vgdisplay:
        # 1     2 3 4 5 6 7 8 9 0 1 12      13      4 5 16      7
        line_split = line.strip().split(':')
        assert len(line_split) == 17
        vg_name = line_split[0]
        vg_size = line_split[11]
        pe_size = line_split[12]
        free_pe = line_split[15]
        vg_size_GiB = float(vg_size) / 1024.0 / 1024.0
        vg_free_GiB = float(pe_size) * float(free_pe) / 1024.0 / 1024.0
        print(template.format(
            hostname, vg_name, 'size_GiB', vg_size_GiB, timestamp
        ))
        print(template.format(
            hostname, vg_name, 'free_GiB', vg_free_GiB, timestamp
        ))
        print(template.format(
            hostname, vg_name, 'free_pe', free_pe, timestamp
        ))


if __name__ == '__main__':
    main()
