#!/usr/bin/env python
#
# igcollect - haproxy
#
# Copyright (c) 2017 InnoGames GmbH
#

from socket import socket, AF_UNIX, SOCK_STREAM, MSG_DONTWAIT
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from time import time

BUFFER_SIZE = 4096


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='haproxy')
    parser.add_argument(
        '--haproxy_stats_socket', default='/var/run/haproxy.stat')

    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{}.{} {} ' + str(int(time()))
    haproxy_info = read_ha_proxy_stats(args.haproxy_stats_socket)
    haproxy_info = haproxy_info.splitlines()
    header = haproxy_info[0].replace(' ', '_').split(',')
    for line in haproxy_info[1:-1]:
        service_data = line.split(',')
        data = dict(zip(header, service_data))  # gather data for every proxy/service
        pxname = data.pop('#_pxname')  # pxname - proxy name; svname - service name
        svname = data.pop('svname')
        for metric_name, metric_value in data.items():
            print(template.format(pxname, svname, metric_name, metric_value))


def read_ha_proxy_stats(haproxy_stats_socket):
    conn = socket(AF_UNIX, SOCK_STREAM)
    try:
        conn.connect(haproxy_stats_socket)
        conn.sendall('show stat\r\n')
        data = conn.recv(BUFFER_SIZE, MSG_DONTWAIT)
        while len(data) % BUFFER_SIZE == 0:
            try:
                data += conn.recv(BUFFER_SIZE, MSG_DONTWAIT)
            except socket.error:
                break
        return data
    finally:
        conn.close()


if __name__ == '__main__':
    main()
