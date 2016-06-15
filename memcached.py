#!/usr/bin/env python
#
# igcollect - Memcached
#
# Copyright (c) 2016, InnoGames GmbH
#

import telnetlib
import sys
import socket
import time


def main(host='127.0.0.1', port='11211'):
    hostname = socket.gethostname().replace('.', '_')
    ts = str(int(time.time()))
    template = 'servers.' + hostname + '.software.memcached.{1} {2} ' + ts

    for line in command(host, port, 'stats').splitlines():
        if line.startswith('STAT '):
            header, key, value = line.split()
            if key.replace('_', '').isalpha() and is_float(value):
                print(template.format(hostname, key, value))


def command(host,  port, cmd):
    """Write a command to telnet and return the response"""
    client = telnetlib.Telnet(host, port)
    client.write(cmd + '\n')
    return client.read_until('END')


def is_float(value):
    try:
        float(value)
    except ValueError:
        return False
    else:
        return True


if __name__ == '__main__':
    main(*sys.argv[1:])
