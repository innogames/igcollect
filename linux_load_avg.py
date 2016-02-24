#!/usr/bin/python
#
# Graphite PostgreSQL Service Data Collector
#
# Copyright (c) 2015, InnoGames GmbH
#

from __future__ import print_function
import socket, time, sys

def main():
    try:
        with open('/proc/loadavg', 'r') as file_descriptor:
            avg01, avg05, avg15 = file_descriptor.readline().strip().split(' ')[:3]
    except:
        sys.exit(1)

    now = str(int(time.time()))
    hostname = socket.gethostname().replace('.', '_')
    template = 'servers.' + hostname + '.system.load.{0} {1} ' + now

    print(template.format('avg01', avg01))
    print(template.format('avg05', avg05))
    print(template.format('avg15', avg15))

if __name__ == '__main__':
    main()
