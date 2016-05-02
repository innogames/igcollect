#!/usr/bin/env python
#
# igcollect - PHP FPM
#
# This is the data collector for the PHP FPM status page.  It makes a
# HTTP request to get the page, and formats the output.  All the numeric
# values of the requested pool is printed.
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function

import urllib2
import socket
import time

from argparse import ArgumentParser

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='servers.{hostname}.software.php_fpm')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--address')
    parser.add_argument('--location', default='/fpm-status') 
    parser.add_argument('--pool', default='www') 

    return vars(parser.parse_args())

def main(prefix, host, location, pool, address=None):
    """The main program"""

    url = 'http://' + (address or host) + location
    request = urllib2.Request(url, headers={'Host': host})
    response = urllib2.urlopen(request)

    hostname = socket.gethostname().replace('.', '_')
    now = str(int(time.time()))
    prefix = prefix.format(hostname=hostname)

    pool_found = False
    for line in response.readlines():
        key, value = line.split(':', 1)
        key = key.replace(' ', '_')
        value = value.strip()

        if key == 'pool':
            pool_found = value == pool

        if pool_found and value.isdigit():
            print(prefix + '.' + key, value.strip(), now)

if __name__ == '__main__':
    main(**parse_args())
