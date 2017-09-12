#!/usr/bin/env python
#
# igcollect - Linux network
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='network')
    return parser.parse_args()


def main():
    args = parse_args()
    now = str(int(time()))
    metric_names = (
        ('rx_bytes', 'bytesIn'),
        ('tx_bytes', 'bytesOut'),
        ('rx_packets', 'pktsIn'),
        ('rx_errs', 'errsIn'),
        ('tx_errs', 'errsOut'),
        ('rx_drop', 'dropIn'),
        ('tx_drop', 'dropOut'),
        ('rx_fifo', 'fifoIn'),
        ('tx_fifo', 'fifoOut'),
        ('rx_frame', 'frameIn'),
        ('tx_colls', 'collsOut'),
        ('tx_carrier', 'carrierOut'),
    )

    nd = get_netdev_dict()
    for interface in nd:
        if interface.startswith('vif'):
            continue
        for key, name in metric_names:
            print('{}.{}.{} {} {}'.format(
                args.prefix, interface.replace('.', '_'),
                name, nd[interface][key], now
            ))


def get_netdev_dict():
    """Return a dictionary made from /proc/net/dev"""

    with open('/proc/net/dev', 'r') as nd:
        netdev_data = nd.readlines(1024)

    netdev_dict = {}
    header = []

    for line in netdev_data:
        if 'Inter' in line:
            # Header 1
            pass
        elif ' face |bytes' in line:
            # Header 2
            a, rx_header, tx_header = line.split('|')
            for i in rx_header.split():
                header.append('rx_' + i)
            for i in tx_header.split():
                header.append('tx_' + i)
        else:
            # We have to handle some kind of interface.  It should be
            # first the interface name, than the counters mentioned
            # in the header.
            x = line.strip().split()
            if_name = x.pop(0).strip(' :')
            netdev_dict[if_name] = {}
            for i in header:
                netdev_dict[if_name][i] = x.pop(0)

    return netdev_dict


if __name__ == '__main__':
    main()
