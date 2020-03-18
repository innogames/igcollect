#!/usr/bin/env python3

"""igcollect - Latency collection
Copyright (c) 2020 InnoGames GmbH

This script is used to collect ping data to evaluate availability and latency
of our network and make it easy to create a Graphite Dashboard

Please note that the package fping has to be installed on your Linux server!

"""

import argparse
import subprocess
import time

from multiprocessing import Pool
from os import cpu_count
from statistics import stdev


def parse_args():
    """ collects parameters to know where and how to ping

     Returns:
         args: the args given to argparse

    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Ping collector script for Graphite ')
    parser.add_argument('hosts', nargs='+',
                        help='the hosts to ping')
    parser.add_argument('-c', '--count', type=int, default=20,
                        choices=range(1,60),
                        help='how many times the script will try to ping '
                             '(number has to be bigger '
                             'than 1 and smaller than 60)')
    parser.add_argument('-p', '--prefix',
                        default='ping',
                        help='the path to the value in Graphite ')
    parser.add_argument('-t', '--timeout', type=int, default=500,
                        help='Initial target timeout in milliseconds. '
                             'the amount of time that program '
                             'waits for a response')
    parser.add_argument('-d', '--delay', type=int, default=1800,
                        choices=range(0,5000),
                        help='time to wait between a series of pings in '
                             'milliseconds')
    return parser.parse_args()


def main():
    """ main function to control Multitasking the collection of the pings """

    args = parse_args()

    chunked_hosts = [args.hosts[i:i + 10]
                     for i in range(0, len(args.hosts), 10)]

    data = [(args.prefix, chunk, args.count, args.timeout, args.delay)
            for chunk in chunked_hosts]

    with Pool(cpu_count() * 2) as p:
        p.starmap(check_pings, data)


def check_pings(prefix, hosts, count, timeout, delay):
    """ checks the pings and prints them

        Parameters:
            prefix (str): were the script will put the data in graphite
            hosts (list(str)):  all the hosts that get pinged
            count (int): how many times a individual host get pinged
            timeout (int): the time till the timeout of fping
            delay (int): time to wait between a series of pings

    """

    values = pings(hosts, count, timeout, delay)

    timestamp = str(int(time.time()))

    for data in values:
        print_ping(prefix, data, timestamp)


def pings(hosts, count, timeout, delay):
    """ pings the host and calculates all data needed

        Parameters:
            hosts (list(str): all the hosts that get pinged
            count (int): how many times a individual host get pinged
            timeout (int): the time till the timeout of fping
            delay (int): time to wait between a series of pings

        Returns:
            values (list(dict(float))): all data gathered for all pinged hosts
    """

    hosts_string = ' '.join(hosts)
    cmd = 'fping -B1 -q -C {} -p {} -t {} {}'
    cmd = cmd.format(count, delay, timeout, hosts_string)
    # output:
    # example.com : 105.94 - 104.78
    # Showing times for each ping. A ping timeout will be shown as '-'.
    output = subprocess.getoutput(cmd).split('\n')

    values = []
    for line in output:
        data = {}
        parts = line.split(':', 1)
        data['dest'] = parts[0].strip(' ').replace('.', '_')
        pings = parts[1].split()

        total = 0.0
        fails = 0
        for i, ping in enumerate(pings):
            if ping == '-':
                pings[i] = -1.0
                fails += 1
            else:
                pings[i] = float(ping)
                total += float(ping)

        data['max'] = max(pings)
        data['min'] = min(pings)

        data['pings'] = pings
        if (len(pings) <= fails):
            data['avg'] = -1
        else:
            avg = total / (len(pings) - fails)
            data['avg'] = avg

        data['fails'] = fails

        data['std'] = stdev(pings)

        values.append(data)

    return values


def print_ping(prefix, data, timestamp):
    """ prints the data in a format we can collect

        Parameters:
            prefix (str): were the script will put the data in graphite
            data (dict(floar)): the data gathered (pings, min, may, avg, std)
            timestamp (str): the timestamp as a number

    """

    pings = data['pings']

    template = (
        prefix + '.' + data['dest'] + '.{} {} ' + timestamp
    )

    for num, ping in enumerate(pings, 1):
        print(template.format('ping' + str(num), ping))

    print(template.format('fails', data['fails']))

    if len(pings):
        # If the length is 0 we ignore the entries

        print(template.format('fails/1', data['fails'] / len(pings)))

        print(template.format('std', data['std']))
        print(template.format('min', data['min']))
        print(template.format('max', data['max']))
        print(template.format('avg', data['avg']))


if __name__ == '__main__':
    main()
