#!/usr/bin/env python

from __future__ import print_function
import socket, time
import subprocess

def get_uptime():
    u=open('/proc/uptime','r')
    uptime=u.readline().split(' ')[0]
    u.close()
    return(uptime)

def get_xminfo_dict(xmdata=False):
    xminfo={}

    for line in xmdata:
        xminfo[line.split(':')[0].strip()]=line.split(':')[1].strip()

    return(xminfo)

xmdata = subprocess.Popen("/usr/sbin/xm info", shell=True, bufsize=8192, stdout=subprocess.PIPE).stdout.readlines()
graphite_data=''
hostname = socket.gethostname().replace('.','_')
now = str(int(time.time()))

xminfo=get_xminfo_dict(xmdata)

uptime=get_uptime()

graphite_data += 'servers.%s.virtualisation.uptime %s %s\n' % (hostname,uptime, now )
graphite_data += 'servers.%s.virtualisation.xen.nr_cpus  %s %s\n' % (hostname,int(xminfo['nr_cpus']), now )
graphite_data += 'servers.%s.virtualisation.xen.total_memory  %s %s\n' % (hostname,int(xminfo['total_memory']), now )
graphite_data += 'servers.%s.virtualisation.xen.free_memory  %s %s\n' % (hostname,int(xminfo['free_memory']), now )

print(graphite_data)
