#!/usr/bin/env python3
#
# igcollect - Linux NUMA memory
#
# Copyright (c) 2016, InnoGames GmbH
#

import time, sys
from socket import gethostname

timestamp = str(int(time.time()))
hostname = gethostname().replace('.', '_')

template = "servers.{0}.system.numa.node{1}.{2} {3} {4}"

# utility to read and parse a comma delimited file (meminfo)
def parse_split_file(filename):
    try:
        with open(filename, 'r') as f:
            return [line.strip().split(None, 1) for line in f]
    except:
        sys.exit(1)

def get_numa_nodes():
    # does not support offline nodes seperates with ','
    nodes = list()
    with open('/sys/devices/system/node/online') as f:
        line = f.readline().rstrip()
    if '-' in line:
        # range of nodes
        max = line.split('-')[1]
    # max is exclusive in range so plus 1
        nodes = range(0,int(max)+1)
    else:
        # We don't need stats for servers with only one node
        sys.exit(0)
    print(nodes)
    return nodes

for node in get_numa_nodes():
    with open('/sys/devices/system/node/node{0}/meminfo'.format(node)) as f:
        lines = [line.strip().split() for line in f]
    stats = dict()
    for line in lines:
        stats[line[2].rstrip(':')] = int(line[3]) # 1024
    for field in stats.keys():
        print(template.format(hostname, node, field, stats[field], timestamp))
