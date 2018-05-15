#!/usr/bin/env python
#
# igcollect - Linux network
#
# Copyright (c) 2018, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time
from os import listdir
from os.path import isdir, islink, join


class InterfaceStatistics(object):
    def _check_dir(self, dev, directory):
        return isdir(join(self._scn, dev, directory))

    def _check_name(self, dev, name):
        return dev == name

    def _check_symlink(self, dev, symlink):
        return islink(join(self._scn, dev, symlink))

    def _check_type(self, dev, types):
        with open(join(self._scn, dev, 'type'), 'r') as fd:
            dev_type = fd.readline().strip()
        return any(dev_type == t for t in types)

    def _check_uevent(self, dev, string):
        with open(join(self._scn, dev, 'uevent'), 'r') as fd:
            return string in fd.read()

    def _read_stat(self, dev, param):
        with open(join(self._scn, dev, 'statistics', param)) as fd:
            return int(fd.readline().strip())

    # Supported types of interfaces for a metrics sending
    # If there is more than one conditions they multipied by AND
    NET_TYPES = {
        'bond': (_check_dir, 'bonding'),
        'bond_slave': (_check_dir, 'bonding_slave'),
        'bridge': (_check_dir, 'bridge'),
        'bridge_slave': (_check_dir, 'brport'),
        'general_slave': (_check_symlink, 'master'),
        'lo': (_check_type, ('772', )),
        'ovs-br0': (_check_name, 'br0'),
        'ovs-system': (_check_name, 'ovs-system'),
        'phys': (_check_symlink, 'device'),
        'tunnel': (_check_type, ('768', '776')),
        'vlan': (_check_uevent, "DEVTYPE=vlan"),
    }
    _scn = '/sys/class/net'

    def __init__(self, included_types=[]):
        self.included_types = included_types
        self.netdev_stat = {}

    def get_interfaces(self):
        for dev in listdir(self._scn):
            dev_path = join(self._scn, dev)
            if not (islink(dev_path) or isdir(dev_path)):
                # Skip regular files
                continue
            if not self.included_types:
                # Send metrics for all devices
                self.netdev_stat[dev] = {}
                continue
            for i_type in self.included_types:
                checks = self.NET_TYPES[i_type]
                results = []
                for check, arg in zip(checks[::2], checks[1::2]):
                    results.append(check(self, dev, arg))
                if False not in results:
                    self.netdev_stat[dev] = {}

    def fill_metrics(self):
        self.timestamp = int(time())
        metric_names = {
            'bytesIn': ['rx_bytes'],
            'bytesOut': ['tx_bytes'],
            'pktsIn': ['rx_packets'],
            'pktsOut': ['tx_packets'],
            'errsIn': ['rx_errors'],
            'errsOut': ['tx_errors'],
            'dropIn': [
                'rx_dropped',
                'rx_missed_errors'
            ],
            'dropOut': ['tx_dropped'],
            'fifoIn': ['rx_fifo_errors'],
            'fifoOut': ['tx_fifo_errors'],
            'frameIn': [
                'rx_length_errors',
                'rx_over_errors',
                'rx_crc_errors',
                'rx_frame_errors'
            ],
            'collsOut': ['collisions'],
            'carrierOut': [
                'tx_carrier_errors',
                'tx_aborted_errors',
                'tx_window_errors',
                'tx_heartbeat_errors'
            ],
        }
        virt_metrics = [
            'bytesIn',
            'bytesOut',
            'pktsIn',
            'pktsOut',
        ]
        if self.netdev_stat == {}:
            self.get_interfaces()
        for dev in self.netdev_stat:
            # We send all metrics only for physical devices
            if self._check_symlink(dev, 'device'):
                dev_metrics = metric_names.keys()
            else:
                dev_metrics = virt_metrics
            for m in dev_metrics:
                self.netdev_stat[dev][m] = 0
                for param in metric_names[m]:
                    self.netdev_stat[dev][m] += self._read_stat(dev, param)

    def print_metrics(self, prefix):
        for dev in self.netdev_stat:
            for metric in self.netdev_stat[dev]:
                print('{}.{}.{} {} {}'.format(
                    prefix, dev.replace('.', '_'), metric,
                    self.netdev_stat[dev][metric], self.timestamp
                ))


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='network')
    parser.add_argument('--enabled-types', action='append',
                        default=[],
                        choices=InterfaceStatistics.NET_TYPES.keys(),
                        help='list of enabled interfaces')
    return parser.parse_args()


def main():
    args = parse_args()
    ns = InterfaceStatistics(args.enabled_types)
    ns.fill_metrics()
    ns.print_metrics(args.prefix)


if __name__ == '__main__':
    main()
