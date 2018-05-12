#!/usr/bin/env python
"""igcollect - Beanstalkd

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_STREAM
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='beanstalkd')
    return parser.parse_args()


def main():
    """The main program

    It gets the statistics from the local Beanstalkd service and prints them
    in the format of the Graphite.
    """
    args = parse_args()
    template = args.prefix + '.stats.{} {} ' + str(int(time()))
    metrics = (
        'current-jobs-urgent',
        'current-jobs-ready',
        'current-jobs-reserved',
        'current-jobs-delayed',
        'current-jobs-buried',
        'cmd-put',
        'cmd-peek',
        'cmd-peek-ready',
        'cmd-peek-delayed',
        'cmd-peek-buried',
        'cmd-reserve',
        'cmd-reserve-with-timeout',
        'cmd-delete',
        'cmd-release',
        'cmd-use',
        'cmd-watch',
        'cmd-ignore',
        'cmd-bury',
        'cmd-kick',
        'cmd-touch',
        'cmd-stats',
        'cmd-stats-job',
        'cmd-stats-tube',
        'cmd-list-tubes',
        'cmd-list-tube-used',
        'cmd-list-tubes-watched',
        'cmd-pause-tube',
        'job-timeouts',
        'total-jobs',
        'current-tubes',
        'current-connections',
        'current-producers',
        'current-workers',
        'current-waiting',
        'total-connections',
        'rusage-utime',
        'rusage-stime',
        'binlog-oldest-index',
        'binlog-current-index',
        'binlog-records-migrated',
        'binlog-records-written',
    )
    stats = [l.split(b': ') for l in read_stats().splitlines()[2:-1]]

    for key, value in stats:
        if key.decode('utf-8') in metrics:
            print(template.format(key.decode('utf-8'), value.decode('utf-8')))


def read_stats():
    """Read the stats from the local Beanstalkd service

    Beanstalkd implements Memcached like simple TCP plain text protocol.
    It is enough to send "stats" request to it to get the metrics.  It is
    capable of handling multiple requests with a single connection, so
    the connection will remain open after the response.  It also returns
    the length of the response for us to know how many bytes we need to
    read.  Thought, we won't bother with those details.  We don't need to
    reuse the connection.  We will fetch 4096 bytes which is more than
    enough for the stats.

    We want to make sure that the connection is closed in any case and
    the program wouldn't hang waiting for the server to respond.  We will use
    2 second timeout to achieve this.
    """
    conn = socket(AF_INET, SOCK_STREAM)
    try:
        conn.settimeout(2)
        conn.connect(('localhost', 11300))
        conn.send(b'stats\r\n')
        return conn.recv(4096)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
