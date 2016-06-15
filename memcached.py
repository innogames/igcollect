#!/usr/bin/env python
#
# igcollect - Memcached
#
# Copyright (c) 2016, InnoGames GmbH
#

import re
import telnetlib
import sys
import socket
import time

stat_regex = re.compile(ur'STAT (.*) (.*)\r')


def main(host='127.0.0.1', port='11211'):
    stats = dict(stat_regex.findall(command(host, port, 'stats')))
    hostname = socket.gethostname().replace('.', '_')
    ts = str(int(time.time()))
    template = 'servers.' + hostname + '.software.memcached.{1} {2} ' + ts

    for key in stats:
        print(template.format(hostname, key, stats[key]))


def command(host,  port, cmd):
    """Write a command to telnet and return the response"""
    client = telnetlib.Telnet(host, port)
    client.write(cmd + '\n')
    return client.read_until('END')


if __name__ == '__main__':
    main(*sys.argv[1:])
