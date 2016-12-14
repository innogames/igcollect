#!/usr/bin/env python
#
# igcollect - Rabbitmq stat
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import json
import urllib2
import base64
import socket
import calendar
import time

def download(url):
    base64string = base64.encodestring('%s:%s' % ('guest', 'guest'))[:-1]
    req = urllib2.Request(url)
    req.add_header("Authorization", "Basic %s" % base64string)
    r = urllib2.urlopen(req)
    return json.load(r)

rabbit_url = 'http://localhost:15672/api'
graphite_prefix = 'servers.' + socket.gethostname().replace('.', '_') + '.software.rabbitmq'
now = calendar.timegm(time.gmtime())
nodes_metrics = ['fd_used', 'fd_total', 'sockets_used', 'sockets_total',
                'mem_used', 'mem_limit', 'disk_free', 'disk_free_limit',
                'proc_used', 'proc_total', 'run_queue', 'processors']

overview_object_totals_metrics = ['consumers', 'queues', 'exchanges', 'connections', 'channels']

overview_message_stats_metrics = ['publish']

data = download(rabbit_url + '/overview')
nodename = data['node']

for metric in overview_object_totals_metrics:
    print(graphite_prefix + '.object_totals.' + metric + ' ' + str(data['object_totals'][metric]) + ' ' + str(now))

for metric in overview_message_stats_metrics:
    print(graphite_prefix + '.message_stats.' + metric + ' ' + str(data['message_stats'][metric]) + ' ' + str(now))

data = download(rabbit_url + '/nodes/' + nodename)

for metric in nodes_metrics:
    print(graphite_prefix + '.' + metric + ' ' + str(data[metric]) + ' ' + str(now))
