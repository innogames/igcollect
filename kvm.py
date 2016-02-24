#!/usr/bin/python

import time
import socket
import libvirt
import xml.etree.ElementTree as ET

conn = libvirt.openReadOnly(None)
domids = conn.listDomainsID()

hostname = socket.gethostname().replace('.','_')
now = str(int(time.time()))
message = ''

for ID in domids:
    dom = conn.lookupByID(ID)
    name = dom.name().replace('.','_')
    total_cpu = 0
    for vcpu in dom.vcpus()[0]:
        cputime = vcpu[2] / 1E9
        message += 'servers.{0}.virtualisation.vserver.{1}.vcpu.{2}.time {3} {4}\n'.format(hostname,name,vcpu[0],cputime,now)
        total_cpu += cputime
    message += 'servers.{0}.virtualisation.vserver.{1}.vcpu.time {2} {3}\n'.format(hostname,name,total_cpu,now)
    tree = ET.fromstring(dom.XMLDesc())
    for target in tree.findall('devices/interface/target'):
        dev = target.attrib['dev']
        stats = dom.interfaceStats(dev)
        message += 'servers.{0}.virtualisation.vserver.{1}.net.{2}.bytesIn {3} {4}\n'.format(hostname,name,dev,stats[0],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.net.{2}.bytesOut {3} {4}\n'.format(hostname,name,dev,stats[4],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.net.{2}.pktsIn {3} {4}\n'.format(hostname,name,dev,stats[1],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.net.{2}.pktsOut {3} {4}\n'.format(hostname,name,dev,stats[5],now)
    for target in tree.findall('devices/disk/target'):
        dev = target.attrib['dev']
        stats = dom.blockStatsFlags(dev)
        message += 'servers.{0}.virtualisation.vserver.{1}.disk.{2}.bytesRead {3} {4}\n'.format(hostname,name,dev,stats['rd_bytes'],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.disk.{2}.bytesWrite {3} {4}\n'.format(hostname,name,dev,stats['wr_bytes'],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.disk.{2}.iopsRead {3} {4}\n'.format(hostname,name,dev,stats['rd_operations'],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.disk.{2}.iopsWrite {3} {4}\n'.format(hostname,name,dev,stats['wr_operations'],now)
        message += 'servers.{0}.virtualisation.vserver.{1}.disk.{2}.ioTimeMs_read {3} {4}\n'.format(hostname,name,dev,stats['rd_total_times'] / 1E6,now)
        message += 'servers.{0}.virtualisation.vserver.{1}.disk.{2}.ioTimeMs_write {3} {4}\n'.format(hostname,name,dev,stats['wr_total_times'] / 1E6,now)

print message
