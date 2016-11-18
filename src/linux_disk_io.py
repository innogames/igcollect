#!/usr/bin/env python
#
# igcollect - Linux disk I/O
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='linux.disk')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
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
            print(template.format(disk, name, value))


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
