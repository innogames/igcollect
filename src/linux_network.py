#!/usr/bin/env python
#
# igcollect - Linux network
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import socket
import time
import sys


def resolve_to_vserver(vifname=False):
    ''' returns the vserver name for a given virtual network interface'''


def get_netdev_dict():
    ''' returns a dictionary made from /proc/net/dev '''

    try:
        nd = open('/proc/net/dev', 'r')
        netdev_data = nd.readlines(1024)
        nd.close()
    except:
        sys.exit(1)

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
            ''' here we have to handle some kind of interface
            first the interface name than the counters as mentioned
            in the header'''

            x = line.strip().split()
            if_name = x.pop(0).strip(' :')
            netdev_dict[if_name] = {}
            for i in header:
                netdev_dict[if_name][i] = x.pop(0)

    return(netdev_dict)

graphite_data = ''
hostname = socket.gethostname().replace('.', '_')
now = str(int(time.time()))

nd = get_netdev_dict()
for interface in nd:
    if not interface.startswith('vif'):
        graphite_data += 'servers.%s.system.network.%s.bytesIn %s %s\n' % (
            hostname, interface, str(nd[interface]['rx_bytes']), now)
        graphite_data += 'servers.%s.system.network.%s.bytesOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_bytes']), now)
        graphite_data += 'servers.%s.system.network.%s.pktsIn %s %s\n' % (
            hostname, interface, str(nd[interface]['rx_packets']), now)
        graphite_data += 'servers.%s.system.network.%s.pktsOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_packets']), now)
        graphite_data += 'servers.%s.system.network.%s.errsIn %s %s\n' % (
            hostname, interface, str(nd[interface]['rx_errs']), now)
        graphite_data += 'servers.%s.system.network.%s.errsOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_errs']), now)
        graphite_data += 'servers.%s.system.network.%s.dropIn %s %s\n' % (
            hostname, interface, str(nd[interface]['rx_drop']), now)
        graphite_data += 'servers.%s.system.network.%s.dropOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_drop']), now)
        graphite_data += 'servers.%s.system.network.%s.fifoIn %s %s\n' % (
            hostname, interface, str(nd[interface]['rx_fifo']), now)
        graphite_data += 'servers.%s.system.network.%s.fifoOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_fifo']), now)
        graphite_data += 'servers.%s.system.network.%s.frameIn %s %s\n' % (
            hostname, interface, str(nd[interface]['rx_frame']), now)
        graphite_data += 'servers.%s.system.network.%s.collsOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_colls']), now)
        graphite_data += 'servers.%s.system.network.%s.carrierOut %s %s\n' % (
            hostname, interface, str(nd[interface]['tx_carrier']), now)

print(graphite_data)
