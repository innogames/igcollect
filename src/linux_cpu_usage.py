#!/usr/bin/env python
#
# igcollect - Linux CPU usage
#
# Copyright (c) 2016, InnoGames GmbH
#

import socket
import time


def main():
    now = str(int(time.time()))
    hostname = socket.gethostname().replace('.', '_')
    header = (
        'user',
        'nice',
        'system',
        'idle',
        'iowait',
        'irq',
        'softirq',
        'steal',
    )
    cs, totals, uptime, count, intr, ctxt = get_cpustats_dict(header)

    for cpu in cs:
        for metric in header:
            print(
                'servers.{}.system.cpu.{}.{} {} {}'
                .format(hostname, cpu, metric, cs[cpu][metric], now)
            )

    for value in totals:
        print(
            'servers.{}.system.cpu.{} {} {}'
            .format(hostname, value, totals[value], now)
        )

    print('servers.{}.system.cpu.count {} {}'.format(hostname, count, now))
    print('servers.{}.system.cpu.uptime {} {}'.format(hostname, uptime, now))
    print('servers.{}.system.cpu.intr {} {}'.format(hostname, intr, now))
    print('servers.{}.system.cpu.ctxt {} {}'.format(hostname, ctxt, now))


def get_cpustats_dict(header):
    ''' returns a dictionary made from /proc/diskstats '''
    sd = open('/proc/stat', 'r')
    stat_data = sd.readlines(16384)
    sd.close()

    total_dict = {}
    uptime = 0
    cpustats_dict = {}
    count = 0
    keys = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq')
    for line in stat_data:
        # Here we have to handle some kind of disk first the name than
        # the counters as mentioned in the header.
        if line.startswith('cpu '):
            values = line.split()
            total_dict = dict(zip(keys, values[1:8]))
            if len(line.strip().split()) == 11:
                total_dict['steal'] = values[8]
                total_dict['guest'] = values[9]
                total_dict['guest_nice'] = values[10]
            else:
                total_dict['steal'] = 0
                total_dict['guest'] = 0
                total_dict['guest_nice'] = 0

            total_dict['time'] = sum((
                int(total_dict['user']),
                int(total_dict['nice']),
                int(total_dict['system']),
                int(total_dict['iowait']),
                int(total_dict['irq']),
                int(total_dict['softirq']),
                int(total_dict['steal']),
            ))

        elif line.startswith('cpu'):
            count += 1
            x = line.strip().split()
            name = x.pop(0).lstrip('cpu')
            cpustats_dict[name] = {}
            for i in header:
                cpustats_dict[name][i] = x.pop(0)
        elif line.startswith('btime '):
            uptime = int(time.time()) - int(line.split(' ', 1)[1])
        elif line.startswith('intr '):
            interrupts = int(line.split(' ', 2)[1])
        elif line.startswith('ctxt '):
            context_switches = int(line.split(' ', 1)[1])

    return (
        cpustats_dict, total_dict, uptime, count, interrupts, context_switches
    )


if __name__ == '__main__':
    main()
