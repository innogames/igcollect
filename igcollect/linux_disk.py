#!/usr/bin/env python
"""igcollect - Linux Disk I/O

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from os import path, listdir
from re import match
from time import time

METRIC_NAMES = {
    'disk': (
        ('major', None),
        ('minor', None),
        ('name', None),
        ('reads', 'iopsRead'),
        ('reads_merged', 'iopsReadMerged'),
        ('sec_read', 'bytesRead'),
        ('ms_read', 'ioTimeMsRead'),
        ('writes', 'iopsWrite'),
        ('writes_merged', 'iopsWriteMerged'),
        ('sec_written', 'bytesWrite'),
        ('ms_written', 'ioTimeMsWrite'),
        ('cur_iops', 'ioOpsInProgress'),
        ('ms_io', 'ioTimeMs'),
        ('weighted_ms_io', 'ioTimesWeighted'),
    ),
    'zfs': (
        ('nread', 'bytesRead'),
        ('nwritten', 'bytesWrite'),
        ('reads', 'iopsRead'),
        ('writes', 'iopsWrite'),
        ('wtime', None),
        ('wlentime', None),
        ('wupdate', None),
        ('rtime', None),
        ('rlentime', None),
        ('rupdate', None),
        ('wcnt', 'ioOpsInProgress'),
        ('rcnt', None),
    )
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='disk')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    

    for disk_name, disk_stats in dict(
        list(get_diskstats_dict().items()) +
        list(get_zpoolstats_dict().items())
    ).items():
        for stat_name, value in disk_stats.items():
            if stat_name != 'type':
                print(template.format(disk_name, stat_name, value))


def get_zpoolstats_dict():
    """Return a dictionary made from /proc/spl/kstat/zfs/"""

    zfs_base = '/proc/spl/kstat/zfs'
    if not path.isdir(zfs_base):
        return {}

    disk_type = 'zfs'
    ret = {}

    for zpool in listdir(zfs_base):
        if not path.isdir('{}/{}'.format(zfs_base, zpool)):
            continue
        ret[zpool] = {'type': 'zfs'}
        with open('{}/{}/io'.format(zfs_base, zpool) , 'r') as fp:
            stats_found = False
            for line in fp:
                if line.startswith('nread'):
                    # Disks stats are after line with headers
                    stats_found = True
                    continue
                if stats_found:
                    x = line.strip().split()
                    ret[zpool] = {'type': disk_type}
                    ret[zpool].update(read_metrics(x, METRIC_NAMES[disk_type]))
                    
    return ret


def get_diskstats_dict():
    """Return a dictionary made from /proc/diskstats"""
    
    disk_type = 'disk'
    ret = {}

    with open('/proc/diskstats', 'r') as fp:
        for line in fp:
            x = line.strip().split()
            disk_name = x[2]
            # Filter for only normal disks
            if not match('^(xv|[shv]|nv)(d[a-z]|me[0-9]n[1-9])$', disk_name):
                continue
            ret[disk_name] = {'type': disk_type}
            ret[disk_name].update(read_metrics(x, METRIC_NAMES[disk_type]))

    return ret


def read_metrics(line, metrics):
    sector_size = 512
    ret = {}
    for stat_key, stat_name in metrics:
        value = line.pop(0)
        if stat_name:
            value = int(value)
            if stat_key.startswith('sec_'):
                value *= sector_size
            ret[stat_name] = value
    return(ret)


if __name__ == '__main__':
    main()
