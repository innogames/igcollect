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
    parser.add_argument('hosts', metavar='h', nargs='+',
                        help='the adresses to ping')
    parser.add_argument('-c', '--count', type=int, default=20,
                        help='how many times should the script tries to ping')
    parser.add_argument('-p', '--prefix', default='ping',
                        help='the path to the value in Graphite')
    parser.add_argument('-t', '--timeout', type=int, default=300,
                        help='time in milliseconds'
                             ' till the timeout is retched')
    return parser.parse_args()


def main():
    args = parse_args()

    chunked_hosts = [args.hosts[i:i + 10]
                     for i in range(0, len(args.hosts), 10)]

    data = [(args.prefix, chunk, args.count, args.timeout)
            for chunk in chunked_hosts]

    with Pool(cpu_count() * 2) as p:
        p.starmap(ping, data)



def ping(prefix, hosts, count, timeout):
    hosts_string = " ".join(hosts)
    # -p calculates the time fping waits between single ping probes
    # fping used 20 probes/min by default und set this value to 1800
    # if you use 30 probes the -p time should goe down, for 10 up
    # 0 would not make any sense to enter in to this script
    cmd = 'fping -B1 -q -C {} -p {} -t {} {}'
    cmd = cmd.format(count, (20/count) * 1800, timeout, hosts_string)

    output = subprocess.getoutput(cmd).split('\n')
    for line in output:
        data = {}
        parts = line.split(':')
        data['dest'] = parts[0].replace(' ', '').replace('.', '_')
        pings = parts[1].split(' ')
        # first value would be empty
        pings.pop(0)

        avg = 0
        for i, ping in enumerate(pings):
            if pings[i] == '-':
                data['ping{}'.format(i)] = -1
            else:
                data['ping{}'.format(i)] = pings[i]
                avg += float(pings[i])
            i += 1

        avg /= len(pings)
        data['avg'] = avg

        pings = pings[0:]
        data['max'] = max(pings)
        data['min'] = min(pings)

        send(prefix, data, count)


def send(prefix, data, count):
    template = str(prefix) + '.{}.{} {} ' + str(int(time.time()))

    fails = 0
    for num in range(count):
        print(template.format(data['dest'], 'ping' + str(num + 1),
                              data['ping' + str(num)]))
        if data['ping' + str(num)] == -1:
            fails += 1

    print(template.format(data['dest'], 'fails', fails))
    print(template.format(data['dest'], 'fails/1', fails / count))

    print(template.format(data['dest'], 'min', data['min']))
    print(template.format(data['dest'], 'max', data['max']))
    print(template.format(data['dest'], 'avg', data['avg']))


if __name__ == '__main__':
    main()
