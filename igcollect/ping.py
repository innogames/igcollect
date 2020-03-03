#!/usr/bin/env python3

"""igcollect - Latency collection
Copyright (c) 2020 InnoGames GmbH
"""

import _thread
import argparse
import subprocess

from time import time, sleep

def parse_args():
    parser = argparse.ArgumentParser(
        description='Ping colecctor script for Graphana ')
    parser.add_argument('adress', metavar='URL', type=str, nargs='+',
                        help='the address zu ping to')
    parser.add_argument('-c', '--count', type=int, default=20,
                        help='how many tims should the script tries to ping')
    parser.add_argument('--prefix', default='ping',
                        help='the path to the value in Graphana')
    return parser.parse_args()


def main():
    args = parse_args()
    hostname = args.adress
    count = args.count
    prefix = args.prefix

    i = 1
    hosts = ''
    for host in hostname:
        hosts += host + ' '
        if i % 10 == 0:
            _thread.start_new_thread(ping, (prefix, hosts, count))
            hosts = ''
    if hosts != '':
        ping(prefix, hosts, count)

    while _thread._count() > 0:
        sleep(1)


def ping(prefix, hosts, count):
    cmd = ('fping -B1 -q -C {} -p {} {}'.format(count, (20/count)*2000, hosts))
    fping = subprocess.getoutput(cmd)
    output = fping.split('\n')
    for line in output:
        data = {}
        part = line.split(':')
        data['dest'] = part[0].replace(' ', '').replace('.', '_')
        pings = part[1].split(' ')
        i = 1
        avg = 0
        while i <= count:
            if pings[i] == '-':
                data['ping{}'.format(i)] = -1
            else:
                data['ping{}'.format(i)] = pings[i]
                avg += float(pings[i])
            i += 1

        avg /= count
        if avg == 0.0:
            data['avg'] = '-'
        else:
            data['avg'] = avg
        pings = pings[1:]
        data['max'] = max(pings)
        data['min'] = min(pings)

        send(prefix, data, count)


def send(prefix, data, count):
    template = prefix + '.{}.{} {} ' + str(int(time()))

    fails = 0
    for num in range(count):
        print(template.format(data['dest'], 'ping' + str(num + 1),
                              data['ping' + str(num + 1)]))
        if data['ping' + str(num + 1)] == -1:
            fails += 1

    print(template.format(data['dest'], 'fails', fails))
    print(template.format(data['dest'], 'fails/1', fails / count))

    print(template.format(data['dest'], 'min', data['min']))
    print(template.format(data['dest'], 'max', data['max']))
    print(template.format(data['dest'], 'avg', data['avg']))


if __name__ == '__main__':
    main()
