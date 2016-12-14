#!/usr/bin/env python
#
# igcollect - Nginx
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
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--url', default='http://localhost/nginx_status')

    return vars(parser.parse_args())


def main(host, url):
    """The main program"""

    hostname = socket.gethostname().replace('.', '_')
    prefix = "servers."+ hostname +".software.nginx."
    stub_status = {}


    #Get information from stub_status page
    headers = {"Host": host}
    f = urllib2.Request(url, headers=headers)
    response = urllib2.urlopen(f)
    s = response.read().splitlines()
    stub_status['active_connections']   = s[0].split(":")[1].strip() #current active connections
    stub_status['accepted_connections'] = s[2].split()[0].strip()    #all accepted connections since server restart
    stub_status['handled_connections']  = s[2].split()[1].strip()    #all connections that were processed
    stub_status['handled_requests']     = s[2].split()[2].strip()    #all requests which were processed
    stub_status['reading']              = s[3].split()[1].strip()    #current reading connections, reads request header
    stub_status['writing']              = s[3].split()[3].strip()    #current writing connections, reads request body, processes request, or writes response to a client
    stub_status['waiting']              = s[3].split()[5].strip()    #keep-alive connections, actually it is active - (reading + writing

    template = prefix + "stub_status.{0} {1} {2}"

    now = str(int(time.time()))

    for key, value in stub_status.items():
        print(template.format(key, value, now))


if __name__ == "__main__":
    main(**parse_args())
