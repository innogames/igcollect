#!/usr/bin/env python
#
# igcollect - Linux NUMA CPUs
#
# Copyright (c) 2016, InnoGames GmbH
#

import itertools
try:
    import libvirt
except ImportError:
    libvirt = None
import os.path
import re
import socket
import sys
import subprocess
import time


def main():
    hostname = socket.gethostname().replace('.', '_')
    # Find cores of each numa node
    core2node = {}
    nodes = []
    for node in itertools.count(0):
        node_dir = '/sys/devices/system/node/node{i}/'.format(i=node)
        if not os.path.isdir(node_dir):
            break
        nodes.append(node)

        cpulist = cat(node_dir + 'cpulist')

        # Expand 0-3,7-11 syntax to explicit list of numbers
        def fix_range(m):
            (start, stop) = [int(g) for g in m.groups()]
            return ','.join([str(i) for i in range(start, stop + 1)])
        cpulist = re.sub(r'(\d+)\-(\d+)', fix_range, cpulist)
        for cpu in cpulist.split(','):
            core2node[int(cpu)] = node

    # Don't track hosts with only one node
    if len(nodes) < 2:
        sys.exit(0)

    #  Aggregate CPU times for each node
    proc_stat_header = [
        'user',
        'nice',
        'system',
        'idle',
        'iowait',
        'irq',
        'softirq',
    ]
    total_stats = {n: {s: 0 for s in proc_stat_header} for n in nodes}
    for line in run("cat /proc/stat | grep -e '^cpu[0-9]'").splitlines():
        stats = line.split()
        cpu = int(stats[0][3:])
        for header, stat in zip(proc_stat_header, stats[1:]):
            total_stats[core2node[cpu]][header] += int(stat)

    # Add numastat values
    for node in nodes:
        total_stats[node]['cpu_count'] = core2node.values().count(node)
        for line in cat(
            '/sys/devices/system/node/node{i}/numastat', i=node
        ).splitlines():
            stat, value = line.split()
            total_stats[node][stat] = int(value)

    for node, node_stats in total_stats.items():
        for key, value in node_stats.items():
            print(
                'servers.{host}.system.numa.node{node}.{key} {value} {now}'
                .format(host=hostname, node=node, key=key, value=value, now=now())
            )

    # VCPU -> node assignment
    conn = libvirt and libvirt.openReadOnly(None)
    if conn is not None:
        result = vm_nodes(conn, core2node, nodes)
        for guest, assignment in result.items():
            for node, num_vcpu in assignment.items():
                print(
                    'servers.{host}.virtualisation.vserver.{guest}.numa.node{node}.vcpu_count {value} {now}'
                    .format(
                        host=hostname,
                        guest=guest.replace('.', '_'),
                        node=node,
                        value=num_vcpu,
                        now=now(),
                    )
                )


def vm_nodes(conn, core2node, nodes):
    result = {}
    for dom in conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE):
        # dom.vcpus returns:
        # ([info, info, ...], [affinity, affinity, ...])
        # Both lists have len() == number of VCPUs
        #
        # Info block:
        #   (<vcpu id>, <?>, <total cpu time?>, <physical core ID>)
        # Affinity block is a tuple with a bool for each physical core.
        vcpu_nodes = [core2node[e[3]] for e in dom.vcpus()[0]]
        name = dom.name()
        result[name] = {}
        for node in nodes:
            result[name][node] = vcpu_nodes.count(node)
    return result


def now():
    return int(time.time())


def run(cmd, **kwargs):
    return subprocess.check_output(cmd.format(**kwargs), shell=True).strip()


def cat(f, **kwargs):
    return run('cat ' + f, **kwargs)


if __name__ == '__main__':
    main()
