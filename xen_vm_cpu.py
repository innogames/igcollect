#!/usr/bin/env python

from __future__ import print_function
import socket, time
import subprocess


def get_vcpulist_dict(xmdata=False,hostname=False):
    vc={}
    for line in xmdata:

        if not line.startswith(('Name','\n',' ')):
            vm_name,vm_id,vm_vcpu,vm_cpu,vm_state,vm_time,vm_affinity = line.split()[:7]
            if vm_name=='Domain-0': vm_name=hostname
            vm_name=vm_name.replace('.','_')

            try:
                vc[vm_name]
            except KeyError:
                vc[vm_name]={}
            vc[vm_name]['id']  = vm_id

            try:
                vc[vm_name]['vcpu']
            except KeyError:
                vc[vm_name]['vcpu'] = {}

            if float(vm_time) > 1:
                vc[vm_name]['vcpu'][vm_vcpu] = vm_time
    return(vc)

xmdata = subprocess.Popen("/usr/sbin/xm vcpu-list", shell=True, bufsize=32678, stdout=subprocess.PIPE).stdout.readlines()
graphite_data=''
hostname = socket.gethostname().replace('.','_')
now = str(int(time.time()))

vcdict = get_vcpulist_dict(xmdata,hostname)

for vserver in vcdict:
    total = 0
    for vcpu in vcdict[vserver]['vcpu']:
        graphite_data += 'servers.%s.virtualisation.vserver.%s.vcpu.%s.time %s %s\n' % (hostname,vserver,vcpu,vcdict[vserver]['vcpu'][vcpu],now)
        total += int(vcdict[vserver]['vcpu'][vcpu].split('.')[0])
    graphite_data += 'servers.%s.virtualisation.vserver.%s.vcpu.time %s %s\n' % (hostname,vserver,total,now)

print(graphite_data)
