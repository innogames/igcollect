#!/usr/bin/env python
#
# igcollect - Linux CPU performance factors
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import socket
import time
import sys

factors = {
    'Intel(R) Xeon(R) CPU           L5520  @ 2.27GHz': 0.8,
    'Intel(R) Xeon(R) CPU           L5640  @ 2.27GHz': 1.0,
    'Intel(R) Xeon(R) CPU E5-2660 0 @ 2.20GHz': 1.2,
    'Intel(R) Xeon(R) CPU E5-2660 v2 @ 2.20GHz': 1.44,
    'Intel(R) Xeon(R) CPU E5-2680 v3 @ 2.50GHz': 1.8,
    'Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz': 1.8
}
cpufactor = 1.0

try:
    cd = open('/proc/cpuinfo', 'r')
    cpu_data = cd.readlines(1024)
    cd.close()
except:
    sys.exit(1)

for line in cpu_data:
    l = line.split(':', 1)[1].strip()
    if l in factors:
        cpufactor = factors[l]
        break

graphite_data = ''
hostname = socket.gethostname().replace('.', '_')
now = str(int(time.time()))
graphite_data += 'servers.%s.hardware.cpuinfo.perffactor %s %s\n' % (
    hostname, cpufactor, now)
print(graphite_data)
