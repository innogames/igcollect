#!/usr/bin/env python
#
# igcollect - XEN VM network
#
# Copyright (c) 2015, InnoGames GmbH

from __future__ import print_function
import socket
import time
import subprocess


def resolve_to_vserver(vifname=False, xmdata=False):
    """Returns the vserver name for a given virtual network interface"""

    vifd = vifname.lstrip('vif').split('.')[0]

    for line in xmdata:
        name = line.split()[0]
        domainid = line.split()[1]

        if domainid == vifd:
            return name.replace('.', '_')


def get_netdev_dict():
    """Returns a dictionary made from /proc/net/dev"""

    nd = open('/proc/net/dev', 'r')
    netdev_data = nd.readlines(1024)
    nd.close()

    netdev_dict = {}
    header = []

    for line in netdev_data:
        if line.find('Inter') != -1:
            ''' header 1 '''
        elif line.find(' face |bytes') != -1:
            ''' header 2 '''
            a, rx_header, tx_header = line.split('|')
            for i in rx_header.split():
                header.append('rx_' + i)
            for i in tx_header.split():
                header.append('tx_' + i)

        else:
            # Here we have to handle some kind of interface.  First,
            # the interface name than the counters as mentioned in the header.
            x = line.strip().split()
            if_name = x.pop(0).strip(' :')
            netdev_dict[if_name] = {}
            for i in header:
                netdev_dict[if_name][i] = x.pop(0)

    return(netdev_dict)

xmdata = subprocess.Popen(
    "/usr/sbin/xm list",
    shell=True,
    bufsize=8192,
    stdout=subprocess.PIPE).stdout.readlines()
hostname = socket.gethostname().replace('.', '_')
now = str(int(time.time()))

nd = get_netdev_dict()
template = 'servers.{0}.virtualisation.vserver.{1}.net.{2}.{3} {4} {5}'
parameters = (
    ('rx_bytes', 'bytesIn'),
    ('tx_bytes', 'bytesOut'),
    ('rx_packets', 'pktsIn'),
    ('tx_packets', 'pktsOut'),
)

for interface in nd:
    vserver = resolve_to_vserver(interface, xmdata)

    if interface.startswith('vif'):
        for source, target in parameters:
            name = interface.replace('.', '_')
            value = nd[interface][source]

            print(template.format(hostname, vserver, name, target, value, now))
