#!/usr/bin/env python
"""igcollect - KVM

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from collections import defaultdict
from itertools import count
from os.path import isdir
from re import sub as regexp_sub
from subprocess import check_output
from time import time
import libvirt
import xml.etree.ElementTree as ET


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='virtualisation')
    parser.add_argument('--trim-domain')
    return parser.parse_args()


def main():
    args = parse_args()
    conn = libvirt.openReadOnly(None)
    dom_ids = conn.listDomainsID()
    now = str(int(time()))
    core2node = get_cpu_core_to_numa_node_mapping()
    for dom_id in dom_ids:
        dom = conn.lookupByID(dom_id)
        name = dom.name()
        if args.trim_domain:
            if name.endswith('.' + args.trim_domain):
                name = name[:-len('.' + args.trim_domain)]
        name = name.replace('.', '_')
        total_cpu = 0
        vcpu_nodes = defaultdict(int)
        for vcpu in dom.vcpus()[0]:
            cputime = vcpu[2] / 1E9
            print(
                '{}.vserver.{}.vcpu.{}.time {} {}'
                .format(args.prefix, name, vcpu[0], cputime, now)
            )
            total_cpu += cputime
            vcpu_nodes[core2node[vcpu[3]]] += 1
        print(
            '{}.vserver.{}.vcpu.time {} {}'
            .format(args.prefix, name, total_cpu, now)
        )
        for node, value in vcpu_nodes.items():
            print(
                '{}.vserver.{}.numa.node{}.vcpu_count {} {}'
                .format(args.prefix, name, node, value, now)
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


def get_cpu_core_to_numa_node_mapping():
    core2node = {}
    for node in count(0):
        node_dir = '/sys/devices/system/node/node{i}/'.format(i=node)
        if not isdir(node_dir):
            break

        cpulist = cat(node_dir + 'cpulist')

        # Expand 0-3,7-11 syntax to explicit list of numbers
        def fix_range(m):
            start, stop = [int(g) for g in m.groups()]
            return ','.join([str(i) for i in range(start, stop + 1)])

        cpulist = regexp_sub(r'(\d+)\-(\d+)', fix_range, cpulist)
        for cpu in cpulist.split(','):
            core2node[int(cpu)] = node
    return core2node


def cat(filename):
    return check_output(['cat', filename]).strip().decode()


if __name__ == '__main__':
    main()
