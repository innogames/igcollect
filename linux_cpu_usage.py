#!/usr/bin/env python

from __future__ import print_function
import socket, time, sys


def get_cpustats_dict(header):
    ''' returns a dictionary made from /proc/diskstats '''
    try:
        sd = open('/proc/stat','r')
        stat_data = sd.readlines(1024)
        sd.close()
    except:
        sys.exit(1)

    total_dict = {}
    uptime = 0
    cpustats_dict = {}
    count = 0
    for line in stat_data:
        ''' here we have to handle some kind of disk
        first the name than the counters as mentioned
        in the header'''

	if  line.startswith('cpu '):
	    if len(line.strip().split()) == 11:
                a, total_dict['user'], total_dict['nice'], total_dict['system'], total_dict['idle'], total_dict['iowait'], total_dict['irq'], total_dict['softirq'], total_dict['steal'], total_dict['guest'], total_dict['guest_nice'] = line.split()

                total_dict['time'] = int(total_dict['user']) +  int(total_dict['nice']) + int(total_dict['system']) + int(total_dict['iowait']) + int(total_dict['irq']) + int(total_dict['softirq']) + int(total_dict['steal'])
	    else:
                 total_dict['steal'] = 0
                 total_dict['guest'] = 0
                 total_dict['guest_nice'] = 0
                 a, total_dict['user'], total_dict['nice'], total_dict['system'], total_dict['idle'], total_dict['iowait'], total_dict['irq'], total_dict['softirq'], a = line.split(' ',8)
                 total_dict['time'] = int(total_dict['user']) +  int(total_dict['nice']) + int(total_dict['system']) + int(total_dict['iowait']) + int(total_dict['irq'])


        elif line.startswith('cpu'):
            count += 1
            x = line.strip().split()
            name = x.pop(0).lstrip('cpu')
            cpustats_dict[name] = {}
            for i in header:
                cpustats_dict[name][i] = x.pop(0)
        elif line.startswith('btime '):
            uptime = int(time.time()) - int(line.split(' ',1)[1])

    return(cpustats_dict, total_dict, uptime, count)


now = str(int(time.time()))
graphite_data=''
hostname = socket.gethostname().replace('.','_')
sector_size=512

header=['user','nice','system','idle','iowait','irq','softirq','steal']
cs, totals, uptime, count = get_cpustats_dict(header)

for cpu in cs:
    for metric in header:
        graphite_data += 'servers.%s.system.cpu.%s.%s %s %s\n' % (hostname,cpu, metric, str(cs[cpu][metric]), now )

for value in totals:
    graphite_data += 'servers.%s.system.cpu.%s %s %s\n' % (hostname, str(value), totals[value], now )

graphite_data += 'servers.%s.system.cpu.count %s %s\n' % (hostname, str(count), now )
graphite_data += 'servers.%s.system.cpu.uptime %s %s\n' % (hostname, str(uptime), now )

print(graphite_data)
