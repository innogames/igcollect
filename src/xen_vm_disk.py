#!/usr/bin/env python
#
# igcollect - Xen VM disks
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import socket
import time
import subprocess
import re


def get_vbds():
    p = subprocess.Popen(['/usr/sbin/xenstore-ls', '-f'],
                         stdout=subprocess.PIPE)
    mapping = dict(line.strip().split(' = ', 1) for line in p.stdout)
    p.wait()
    vbds = {}
    vbd_re = re.compile(r'^/vm/([^/]+)/device/vbd/\d+/backend$')
    for key in mapping:
        match = vbd_re.match(key)
        if match:
            vbd_key = mapping[key][1:-1] + '/physical-device'
            vbd_value = mapping[vbd_key][1:-1]
            name = mapping['/vm/{uid}/name'.format(uid=match.group(1))][1:-1]
            dn_key = mapping[key][1:-1] + '/dev'
            dn_value = mapping[dn_key][1:-1]

            vbds.setdefault(name, {})
            vbds[name].setdefault(dn_value, vbd_value)
    return vbds


def get_diskstats_dict():
    ''' returns a dictionary made from /proc/diskstats '''

    dsd = open('/proc/diskstats', 'r')
    diskstats_data = dsd.readlines(1024)
    dsd.close()

    diskstats_dict = {}
    header = ['major', 'minor', 'name',
              'reads', 'reads_merged', 'sec_read', 'ms_read',
              'writes', 'writes_merged', 'sec_written', 'ms_written',
              'cur_iops', 'ms_io', 'weighted_ms_io']

    header.pop(2)  # just to be able to have also the name in the header

    for line in diskstats_data:
        ''' here we have to handle some kind of disk
        first the name than the counters as mentioned
        in the header'''

        x = line.strip().split()
        disk_name = x.pop(2)
        diskstats_dict[disk_name] = {}
        for i in header:
            diskstats_dict[disk_name][i] = x.pop(0)

    return diskstats_dict


def get_dmname_from_majorminor(diskstats=False, major=0, minor=0):
    for disk in diskstats:
        if (
            int(diskstats[disk]['minor']) == minor and
            int(diskstats[disk]['major']) == major
        ):
            return disk
    return False

graphite_data = ''
hostname = socket.gethostname().replace('.', '_')
now = str(int(time.time()))
sector_size = 512
xenstore_vbd = subprocess.Popen(
    "/usr/sbin/xenstore-ls ",
    shell=True,
    bufsize=8192,
    stdout=subprocess.PIPE).stdout.readlines()
xmlist = subprocess.Popen(
    "/usr/sbin/xm list -l",
    shell=True,
    bufsize=128000,
    stdout=subprocess.PIPE).stdout.readlines()

diskstats = get_diskstats_dict()
vservers = get_vbds()

for server in vservers:
    for device in vservers[server]:
        major, minor = vservers[server][device].strip("'").split(':')
        dmname = get_dmname_from_majorminor(
            diskstats, int(major, 16), int(minor, 16)
        )

        graphite_data += 'servers.%s.virtualisation.vserver.%s.disk.%s.bytesRead %s %s\n' % (
            hostname, server.replace('.', '_'), device, str(int(diskstats[dmname]['sec_read']) * sector_size), now)
        graphite_data += 'servers.%s.virtualisation.vserver.%s.disk.%s.bytesWrite %s %s\n' % (
            hostname, server.replace('.', '_'), device, str(int(diskstats[dmname]['sec_written']) * sector_size), now)
        graphite_data += 'servers.%s.virtualisation.vserver.%s.disk.%s.iopsRead %s %s\n' % (
            hostname, server.replace('.', '_'), device, str(diskstats[dmname]['reads']), now)
        graphite_data += 'servers.%s.virtualisation.vserver.%s.disk.%s.iopsWrite %s %s\n' % (
            hostname, server.replace('.', '_'), device, str(diskstats[dmname]['writes']), now)
        graphite_data += 'servers.%s.virtualisation.vserver.%s.disk.%s.ioTimeMs %s %s\n' % (
            hostname, server.replace('.', '_'), device, str(diskstats[dmname]['ms_io']), now)

print(graphite_data)
