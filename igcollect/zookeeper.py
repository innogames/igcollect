#!/usr/bin/env python
"""igcollect - Zookeeper

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_STREAM, SHUT_WR
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='zookeeper')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{} {} ' + str(int(time()))
    names = {
        'zk_avg_latency',
        'zk_max_latency',
        'zk_min_latency',
        'zk_packets_received',
        'zk_packets_sent',
        'zk_ephemerals_count',
        'zk_approximate_data_size',
        'zk_open_file_descriptor_count',
        'zk_max_file_descriptor_count',
        'zk_znode_count',
        'zk_watch_count',
    }

    data = netcat('localhost', 2181, 'mntr').rstrip('\n')
    for line in data.splitlines():
        key, value = line.split('\t')
        if key in names:
            print(template.format(key, value))


def netcat(hostname, port, content):
    mntr = ''
    conn = socket(AF_INET, SOCK_STREAM)
    conn.connect((hostname, port))
    conn.sendall(content)
    conn.shutdown(SHUT_WR)
    while True:
        data = conn.recv(1024)
        if data == '':
            break
        mntr += data
    conn.close()
    return mntr


if __name__ == '__main__':
    main()
