#!/usr/bin/env python
#
# igcollect - Linux disk I/O
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import socket, time, sys

def resolve_to_vserver(dm_name=False):
    ''' returns the vserver name for a given dm_device'''

def get_diskstats_dict():
    ''' returns a dictionary made from /proc/diskstats '''

    try:
        dsd = open('/proc/diskstats','r')
        diskstats_data = dsd.readlines(1024)
        dsd.close()
    except:
        sys.exit(1)

    diskstats_dict = {}
    header=['major','minor','name',
            'reads','reads_merged','sec_read','ms_read',
            'writes','writes_merged','sec_written','ms_written',
            'cur_iops','ms_io','weighted_ms_io']

    header.pop(2) # just to be able to have also the name in the header

    for line in diskstats_data:
        ''' here we have to handle some kind of disk
        first the name than the counters as mentioned
        in the header'''

        x = line.strip().split()
        disk_name = x.pop(2)
        diskstats_dict[disk_name]={}
        for i in header:
            diskstats_dict[disk_name][i] = x.pop(0)

    return(diskstats_dict)

graphite_data=''
hostname = socket.gethostname().replace('.','_')
now = str(int(time.time()))
sector_size=512

dd = get_diskstats_dict()

for disk in dd:
    # filter for only normal disks and partitions
    if (disk.startswith('sd') or disk.startswith('hd') or disk.startswith('xvd') or disk.startswith('vd')):
        graphite_data += 'servers.%s.system.disk.%s.bytesRead %s %s\n' % (hostname, disk, str(int(dd[disk]['sec_read'])*sector_size), now )
        graphite_data += 'servers.%s.system.disk.%s.bytesWrite %s %s\n' % (hostname, disk, str(int(dd[disk]['sec_written'])*sector_size), now )
        graphite_data += 'servers.%s.system.disk.%s.iopsRead %s %s\n' % (hostname, disk, str(dd[disk]['reads']), now )
        graphite_data += 'servers.%s.system.disk.%s.iopsWrite %s %s\n' % (hostname, disk, str(dd[disk]['writes']), now )
        graphite_data += 'servers.%s.system.disk.%s.ioTimeMsRead %s %s\n' % (hostname, disk, str(dd[disk]['ms_read']), now )
        graphite_data += 'servers.%s.system.disk.%s.ioTimeMsWrite %s %s\n' % (hostname, disk, str(dd[disk]['ms_written']), now )
        graphite_data += 'servers.%s.system.disk.%s.ioTimeMs %s %s\n' % (hostname, disk, str(dd[disk]['ms_io']), now )

print(graphite_data)
