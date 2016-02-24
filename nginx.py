#! /usr/bin/env python
#
# Graphite NGINX Data Collector
#
# Copyright (c) 2015, InnoGames GmbH
# Author: Bernhard Schrader
#

from __future__ import print_function
import fcntl
import urllib2
import socket
import time
import sys

def main():
    """The main program"""

    with open('/tmp/graphite.service.nginx.lock', 'w') as file_descriptor:
        #
        # Exclusive file lock
        #
        # File system locks on UNIX-like systems are advisory, so this lock isn't
        # going to stop anyone from doing anything to this file.  We are locking
        # only for ourself, not for other applications.  It will avoid multiple
        # processes of this script as the second process will die at this point
        # with IOError.
        #
        # Note that we are not going to release the lock.  It will go away with
        # the file descriptor.
        #
        fcntl.lockf(file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

        print_stats()

def print_stats():
    """Print the statistics for Graphite"""

    hostname = socket.gethostname().replace('.', '_')
    prefix = "servers."+ hostname +".software.nginx."
    stub_status = {}


    #Get information from stub_status page
    headers = { "Host": "igsoftware_nginx" }
    f = urllib2.Request("http://127.0.0.1/nginx_status", headers=headers)
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
    main()

