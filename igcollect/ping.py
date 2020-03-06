#!/usr/bin/env python3

"""igcollect - Latency collection
Copyright (c) 2020 InnoGames GmbH
"""

# This script is used to collect ping data to evaluate availability and latency
# of our network and make it easy to create a Graphite Dashboard
#
# Please note that the package fping has to be installed on your Linux server!


import argparse
import subprocess
import time
import socket

from multiprocessing import Pool
from os import cpu_count


def parse_args():
    parser = argparse.ArgumentParser(
        description='Ping collector script for Graphite ')
    parser.add_argument('hosts', nargs='+',
                        help='the hosts to ping')
    parser.add_argument('-c', '--count', type=int, default=20, 
                        choices=range(1,60),
                        help='how many times the script will try to ping '
                             '(number has to be bigger '
                             'than 1 and smaller than 60) (default= 20)')
    parser.add_argument('-p', '--prefix',
                        default='servers.{}.system.ping'.format(
                            socket.gethostname()),
                        help='the path to the value in Graphite '
                             '(default= ping)')
    parser.add_argument('-t', '--timeout', type=int, default=300,
                        help='time in milliseconds '
                             'till the timeout is retched (default= 300)')
    parser.add_argument('-d', '--delay', type=int, default=1800,
                        choices=range(0,5000),
                        help='time to wait between a series of pings '
                             '(default= 1800)')
    return parser.parse_args()


def main():
    args = parse_args()

    chunked_hosts = [args.hosts[i:i + 10]
                     for i in range(0, len(args.hosts), 10)]

    data = [(args.prefix, chunk, args.count, args.timeout, args.delay)
            for chunk in chunked_hosts]

    with Pool(cpu_count() * 2) as p:
        p.starmap(check_pings, data)


def check_pings(prefix, hosts, count, timeout, delay):
    values = pings(hosts, count, timeout, delay)

    timestamp = str(int(time.time()))

    for data in values:
        print_ping(prefix, data, timestamp)
    

def pings(hosts, count, timeout, delay):
    hosts_string = ' '.join(hosts)
    # with 20 probes and 1800 milliseconds in between it takes roughly 1 minute
    # the default value for delay is 1800
    cmd = 'fping -B1 -q -C {} -p {} -t {} {}'
    cmd = cmd.format(count, (20/count) * delay, timeout, hosts_string)

    # example.com : 105.94 - 104.78
    # Showing times for each ping. A ping timeout will be shown as '-'.
    output = subprocess.getoutput(cmd).split('\n')

    values = []
    for line in output:
        data = {}
        parts = line.split(':', 1)
        data['dest'] = parts[0].strip(' ').replace('.', '_')
        pings = parts[1].split()

        data['max'] = max(pings)
        data['min'] = min(pings)
        
        total = 0.0
        fails = 0
        for i, ping in enumerate(pings):
            if ping == '-':
                pings[i] = -1
                fails += 1
            else:
                total += float(ping)

        data['pings'] = pings
        if (len(pings) <= fails):
            data['avg'] = -1
        else:
            avg = total / (len(pings) - fails)
            data['avg'] = avg
            
        data['fails'] = fails

        values.append(data)

    return values


def print_ping(prefix, data, timestamp):
    template = (
        str(prefix) + '.' + data['dest'] + '.{} {} ' + timestamp
    )

    for num, ping in enumerate(data['pings'], 1):
        print(template.format('ping' + str(num), ping))

    print(template.format('fails', data['fails']))

    if len(data['pings']) == 0:
        raise Exception('something went horrible wrong - check your fping -')

    print(template.format('fails/1', data['fails'] / len(data['pings'])))

    print(template.format('min', data['min']))
    print(template.format('max', data['max']))
    print(template.format('avg', data['avg']))


if __name__ == '__main__':
    main()
