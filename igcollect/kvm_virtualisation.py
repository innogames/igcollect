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

# Keep this in sync with igvm!
VG_NAME = 'xen-data'


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='virtualisation')
    parser.add_argument('--trim-domain')
    return parser.parse_args()


def main():
    args = parse_args()
    conn = libvirt.openReadOnly(None)
    now = str(int(time()))
    core2node = get_cpu_core_to_numa_node_mapping()

    total_mem_used = 0

    for dom in conn.listAllDomains():
        name = dom.name()
        if args.trim_domain:
            if name.endswith('.' + args.trim_domain):
                name = name[:-len('.' + args.trim_domain)]
        # Strip objectid from domain name to get the hostname
        if '_' in name:
            name = name.split('_', 1)[1]
        # Make hostname save for graphite
        name = name.replace('.', '_')

        dom_state, dom_reason = dom.state()
        if dom_state == libvirt.VIR_DOMAIN_RUNNING:
            get_dom_vcpu_stats(dom, args.prefix, name, now, core2node)
            get_dom_network_stats(dom, args.prefix, name, now)
            get_dom_disk_stats(dom, args.prefix, name, now)

        total_mem_used += get_dom_memory_stats(dom, args.prefix, name, now)
        get_dom_storage_usage(conn, dom, args.prefix, name, now)

    get_hv_storage_usage(conn, args.prefix, now)
    get_hv_memory_usage(conn, args.prefix, now, total_mem_used)


def get_dom_vcpu_stats(dom, prefix, name, now, core2node):
    total_cpu = 0
    vcpu_nodes = defaultdict(int)
    for vcpu in dom.vcpus()[0]:
        cputime = vcpu[2] / 1E9
        print(
            '{}.vserver.{}.vcpu.{}.time {} {}'
            .format(prefix, name, vcpu[0], cputime, now)
        )
        total_cpu += cputime
        vcpu_nodes[core2node[vcpu[3]]] += 1
    print(
        '{}.vserver.{}.vcpu.time {} {}'
        .format(prefix, name, total_cpu, now)
    )
    for node, value in vcpu_nodes.items():
        print(
            '{}.vserver.{}.numa.node{}.vcpu_count {} {}'
            .format(prefix, name, node, value, now)
        )


def get_dom_network_stats(dom, prefix, name, now):
    tree = ET.fromstring(dom.XMLDesc())
    for target in tree.findall('devices/interface/target'):
        dev = target.attrib['dev']
        stats = dom.interfaceStats(dev)
        print(
            '{}.vserver.{}.net.{}.bytesIn {} {}'
            .format(prefix, name, dev, stats[0], now)
        )
        print(
            '{}.vserver.{}.net.{}.bytesOut {} {}'
            .format(prefix, name, dev, stats[4], now)
        )
        print(
            '{}.vserver.{}.net.{}.pktsIn {} {}'
            .format(prefix, name, dev, stats[1], now)
        )
        print(
            '{}.vserver.{}.net.{}.pktsOut {} {}'
            .format(prefix, name, dev, stats[5], now)
        )


def get_dom_disk_stats(dom, prefix, name, now):
    tree = ET.fromstring(dom.XMLDesc())
    for target in tree.findall('devices/disk/target'):
        dev = target.attrib['dev']
        stats = dom.blockStatsFlags(dev)
        print(
            '{}.vserver.{}.disk.{}.bytesRead {} {}'
            .format(prefix, name, dev, stats['rd_bytes'], now)
        )
        print(
            '{}.vserver.{}.disk.{}.bytesWrite {} {}'
            .format(prefix, name, dev, stats['wr_bytes'], now)
        )
        print(
            '{}.vserver.{}.disk.{}.iopsRead {} {}'
            .format(prefix, name, dev, stats['rd_operations'], now)
        )
        print(
            '{}.vserver.{}.disk.{}.iopsWrite {} {}'
            .format(prefix, name, dev, stats['wr_operations'], now)
        )
        print(
            '{}.vserver.{}.disk.{}.ioTimeMs_read {} {}'
            .format(
                prefix, name, dev, stats['rd_total_times'] / 1E6, now
            )
        )
        print(
            '{}.vserver.{}.disk.{}.ioTimeMs_write {} {}'
            .format(
                prefix, name, dev, stats['wr_total_times'] / 1E6, now
            )
        )


def get_dom_memory_stats(dom, prefix, name, now):
    memory_used = dom.info()[2]
    print(
        '{}.vserver.{}.memory.used {} {}'
        .format(
            prefix, name, memory_used, now,
        )
    )
    return memory_used


def get_hv_memory_usage(conn, prefix, now, memory_used):
    memory_total = conn.getMemoryStats(-1)['total']
    memory_free = memory_total - memory_used
    print(
        '{}.kvm.memory.total {} {}'
        .format(prefix, memory_total, now)
    )
    print(
        '{}.kvm.memory.used {} {}'
        .format(prefix, memory_used, now)
    )
    print(
        '{}.kvm.memory.free {} {}'
        .format(prefix, memory_free, now)
    )


def get_hv_storage_usage(conn, prefix, now):
    for storage_pool in conn.listAllStoragePools():
        info = storage_pool.info()
        name = storage_pool.name()

        print(
            '{}.kvm.storage_pool.{}.total {} {}'
            .format(prefix, name, info[1] // 1024, now)
        )
        print(
            '{}.kvm.storage_pool.{}.used {} {}'
            .format(prefix, name, info[2] // 1024, now)
        )
        print(
            '{}.kvm.storage_pool.{}.free {} {}'
            .format(prefix, name, info[3] // 1024, now)
        )


def get_dom_storage_usage(conn, dom, prefix, name, now):
    tree = ET.fromstring(dom.XMLDesc(0))
    pool = tree.find('./devices/disk/source').get('pool')
    vol  = tree.find('./devices/disk/source').get('volume')

    if pool:
        pool =conn.storagePoolLookupByName(pool)
        vol = pool.storageVolLookupByName(vol)
        info = vol.info()

        print(
            '{}.kvm.vserver.{}.storage.total {} {}'
            .format(prefix, name, info[1] // 1024, now)
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
