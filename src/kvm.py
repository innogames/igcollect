#!/usr/bin/env python
#
# igcollect - KVM stats
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time
import libvirt
import xml.etree.ElementTree as ET


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='kvm')
    return parser.parse_args()


def main():
    args = parse_args()
    conn = libvirt.openReadOnly(None)
    dom_ids = conn.listDomainsID()
    now = str(int(time()))
    for dom_id in dom_ids:
        dom = conn.lookupByID(dom_id)
        name = dom.name().replace('.', '_')
        total_cpu = 0
        for vcpu in dom.vcpus()[0]:
            cputime = vcpu[2] / 1E9
            print(
                '{}.vserver.{}.vcpu.{}.time {} {}'
                .format(args.prefix, name, vcpu[0], cputime, now)
            )
            total_cpu += cputime
        print(
            '{}.vserver.{}.vcpu.time {} {}'
            .format(args.prefix, name, total_cpu, now)
        )
        tree = ET.fromstring(dom.XMLDesc())
        for target in tree.findall('devices/interface/target'):
            dev = target.attrib['dev']
            stats = dom.interfaceStats(dev)
            print(
                '{}.vserver.{}.net.{}.bytesIn {} {}'
                .format(args.prefix, name, dev, stats[0], now)
            )
            print(
                '{}.vserver.{}.net.{}.bytesOut {} {}'
                .format(args.prefix, name, dev, stats[4], now)
            )
            print(
                '{}.vserver.{}.net.{}.pktsIn {} {}'
                .format(args.prefix, name, dev, stats[1], now)
            )
            print(
                '{}.vserver.{}.net.{}.pktsOut {} {}'
                .format(args.prefix, name, dev, stats[5], now)
            )
        for target in tree.findall('devices/disk/target'):
            dev = target.attrib['dev']
            stats = dom.blockStatsFlags(dev)
            print(
                '{}.vserver.{}.disk.{}.bytesRead {} {}'
                .format(args.prefix, name, dev, stats['rd_bytes'], now)
            )
            print(
                '{}.vserver.{}.disk.{}.bytesWrite {} {}'
                .format(args.prefix, name, dev, stats['wr_bytes'], now)
            )
            print(
                '{}.vserver.{}.disk.{}.iopsRead {} {}'
                .format(args.prefix, name, dev, stats['rd_operations'], now)
            )
            print(
                '{}.vserver.{}.disk.{}.iopsWrite {} {}'
                .format(args.prefix, name, dev, stats['wr_operations'], now)
            )
            print(
                '{}.vserver.{}.disk.{}.ioTimeMs_read {} {}'
                .format(
                    args.prefix, name, dev, stats['rd_total_times'] / 1E6, now
                )
            )
            print(
                '{}.vserver.{}.disk.{}.ioTimeMs_write {} {}'
                .format(
                    args.prefix, name, dev, stats['wr_total_times'] / 1E6, now
                )
            )


if __name__ == '__main__':
    main()
