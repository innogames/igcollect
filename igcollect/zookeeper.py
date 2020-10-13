#!/usr/bin/env python
"""igcollect - Zookeeper

Copyright (c) 2020 InnoGames GmbH
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


def netcat(hostname: str, port: int, content: str) -> str:
    data = b''
    conn = socket(AF_INET, SOCK_STREAM)
    conn.connect((hostname, port))
    conn.sendall(content.encode())
    conn.shutdown(SHUT_WR)
    while True:
        answer = conn.recv(1024)
        if not answer:
            break
        data += answer
    conn.close()
    return data.decode()


if __name__ == '__main__':
    main()
