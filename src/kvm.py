#!/usr/bin/env python
#
# igcollect - KVM stats
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
import socket
import libvirt
import xml.etree.ElementTree as ET


def main():
    conn = libvirt.openReadOnly(None)
    dom_ids = conn.listDomainsID()
    hostname = socket.gethostname().replace('.', '_')
    now = str(int(time.time()))
    for dom_id in dom_ids:
        dom = conn.lookupByID(dom_id)
        name = dom.name().replace('.', '_')
        total_cpu = 0
        for vcpu in dom.vcpus()[0]:
            cputime = vcpu[2] / 1E9
            print(
                'servers.{}.virtualisation.vserver.{}.vcpu.{}.time {} {}'
                .format(hostname, name, vcpu[0], cputime, now)
            )
            total_cpu += cputime
        print(
            'servers.{}.virtualisation.vserver.{}.vcpu.time {} {}'
            .format(hostname, name, total_cpu, now)
        )
        tree = ET.fromstring(dom.XMLDesc())
        for target in tree.findall('devices/interface/target'):
            dev = target.attrib['dev']
            stats = dom.interfaceStats(dev)
            print(
                'servers.{}.virtualisation.vserver.{}.net.{}.bytesIn {} {}'
                .format(hostname, name, dev, stats[0], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.net.{}.bytesOut {} {}'
                .format(hostname, name, dev, stats[4], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.net.{}.pktsIn {} {}'
                .format(hostname, name, dev, stats[1], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.net.{}.pktsOut {} {}'
                .format(hostname, name, dev, stats[5], now)
            )
        for target in tree.findall('devices/disk/target'):
            dev = target.attrib['dev']
            stats = dom.blockStatsFlags(dev)
            print(
                'servers.{}.virtualisation.vserver.{}.disk.{}.bytesRead {} {}'
                .format(hostname, name, dev, stats['rd_bytes'], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.disk.{}.bytesWrite {} {}'
                .format(hostname, name, dev, stats['wr_bytes'], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.disk.{}.iopsRead {} {}'
                .format(hostname, name, dev, stats['rd_operations'], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.disk.{}.iopsWrite {} {}'
                .format(hostname, name, dev, stats['wr_operations'], now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.disk.{}.ioTimeMs_read {} {}'
                .format(hostname, name, dev, stats['rd_total_times'] / 1E6, now)
            )
            print(
                'servers.{}.virtualisation.vserver.{}.disk.{}.ioTimeMs_write {} {}'
                .format(hostname, name, dev, stats['wr_total_times'] / 1E6, now)
            )


if __name__ == '__main__':
    main()
