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

from multiprocessing import Pool
from os import cpu_count


def parse_args():
    parser = argparse.ArgumentParser(
        description='Ping collector script for Graphite ')
    parser.add_argument('hosts', nargs='+',
                        help='the hosts to ping')
    parser.add_argument('-c', '--count', type=int, default=20,
                        help='how many times the script will try to ping')
    parser.add_argument('-p', '--prefix', default='ping',
                        help='the path to the value in Graphite')
    parser.add_argument('-t', '--timeout', type=int, default=300,
                        help='time in milliseconds '
                             'till the timeout is retched')
    return parser.parse_args()


def main():
    args = parse_args()

    chunked_hosts = [args.hosts[i:i + 10]
                     for i in range(0, len(args.hosts), 10)]

    data = [(args.prefix, chunk, args.count, args.timeout)
            for chunk in chunked_hosts]

    with Pool(cpu_count() * 2) as p:
        p.starmap(check_pings, data)


def check_pings(prefix, hosts, count, timeout):
    values = pings(hosts, count, timeout)

    for data in values:
        send(prefix, data)
    

def pings(hosts, count, timeout):
    hosts_string = " ".join(hosts)
    # -p calculates the time fping waits between single ping probes
    # fping used 20 probes/min by default und set this value to 1800
    # if you use 30 probes the -p time should goe down, for 10 up
    # 0 would not make any sense to enter in to this script
    cmd = 'fping -B1 -q -C {} -p {} -t {} {}'
    cmd = cmd.format(count, (20/count) * 1800, timeout, hosts_string)

    output = subprocess.getoutput(cmd).split('\n')

    values = []
    for line in output:
        data = {}
        parts = line.split(':')
        data['dest'] = parts[0].replace(' ', '').replace('.', '_')
        pings = parts[1].split(' ')
        # first value would be empty
        pings.pop(0)

        data['max'] = max(pings)
        data['min'] = min(pings)
        
        total = 0
        fails = 0
        for i, ping in enumerate(pings):
            if ping == '-':
                pings[i] = -1
                fails += 1
            else:
                total += float(pings[i])

        data['pings'] = pings

        avg = total / len(pings)
        data['avg'] = avg
        data['fails'] = fails

        values.append(data)

    return values


def send(prefix, data):
    template = \
        str(prefix) + '.' + data['dest'] + '.{} {} ' + str(int(time.time()))

    for num in range(len(data['pings'])):
        print(template.format('ping' + str(num + 1), data['pings'][num]))

    print(template.format('fails', data['fails']))
    print(template.format('fails/1', data['fails'] / len(data['pings'])))

    print(template.format('min', data['min']))
    print(template.format('max', data['max']))
    print(template.format('avg', data['avg']))


if __name__ == '__main__':
    main()
