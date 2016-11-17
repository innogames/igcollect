#!/usr/bin/env python
#
# igcollect - Linux disk I/O
#
# Copyright (c) 2016, InnoGames GmbH
#

import socket
import time


def main():
    hostname = socket.gethostname().replace('.', '_')
    now = str(int(time.time()))
    sector_size = 512
    dd = get_diskstats_dict()
    metric_names = (
        ('sec_read', 'bytesRead'),
        ('sec_written', 'bytesWrite'),
        ('reads', 'iopsRead'),
        ('writes', 'iopsWrite'),
        ('ms_read', 'ioTimeMsRead'),
        ('ms_written', 'ioTimeMsWrite'),
        ('ms_io', 'ioTimeMs'),
        ('cur_iops', 'ioOpsInProgress'),
    )
    for disk in dd:
        # Filter for only normal disks and partitions
        if not any(disk.startswith(p) for p in ('sd', 'hd', 'xvd', 'vd')):
            continue
        for key, name in metric_names:
            value = int(dd[disk][key])
            if key.startswith('sec_'):
                value *= sector_size
            print(
                'servers.{}.system.disk.{}.{} {} {}'
                .format(hostname, disk, name, value, now)
            )


def get_diskstats_dict():
    """Return a dictionary made from /proc/diskstats"""
    dsd = open('/proc/diskstats', 'r')
    diskstats_data = dsd.readlines(1024)
    dsd.close()

    diskstats_dict = {}
    header = ['major', 'minor', 'name',
              'reads', 'reads_merged', 'sec_read', 'ms_read',
              'writes', 'writes_merged', 'sec_written', 'ms_written',
              'cur_iops', 'ms_io', 'weighted_ms_io']

    header.pop(2)  # Just to be able to have also the name in the header

    for line in diskstats_data:
        # Here we have to handle some kind of disk first the name than
        # the counters as mentioned in the header.
        x = line.strip().split()
        disk_name = x.pop(2)
        diskstats_dict[disk_name] = {}
        for name in header:
            diskstats_dict[disk_name][name] = x.pop(0)

    return diskstats_dict


if __name__ == '__main__':
    main()
