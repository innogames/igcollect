#!/usr/bin/env python

from __future__ import print_function
from __future__ import division

from socket import gethostname
import time, sys
import subprocess

try:
    vgdisplay = subprocess.Popen(['vgdisplay -c'], stdout=subprocess.PIPE, shell=True, stdin=subprocess.PIPE,close_fds=True ).stdout.readlines()
except:
    sys.exit(1)

template = "servers.{0}.system.lvm.{1}.{2} {3} {4}"
hostname = gethostname().replace('.','_')
timestamp = str(int(time.time()))

if vgdisplay:
    for line in vgdisplay:
        # 1     2 3 4 5 6 7 8 9 0 1 12      13      4 5 16      7
        vg_name,a,a,a,a,a,a,a,a,a,a,vg_size,pe_size,a,a,free_pe,a = line.strip().split(':')
        vg_size_GiB = int(vg_size) / 1024 / 1024
        vg_free_GiB = int(pe_size) * int(free_pe) / 1024 / 1024
        print(template.format(hostname,vg_name,'size_GiB',vg_size_GiB, timestamp))
        print(template.format(hostname,vg_name,'free_GiB',vg_free_GiB, timestamp))
        print(template.format(hostname,vg_name,'free_pe',free_pe, timestamp))
