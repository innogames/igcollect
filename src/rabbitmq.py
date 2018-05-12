#!/usr/bin/env python
"""igcollect - RabbitMQ

Copyright (c) 2018 InnoGames GmbH
"""

import sys
import json
import base64

from time import time
from argparse import ArgumentParser

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='rabbitmq')
    return parser.parse_args()


def main():
    args = parse_args()
    rabbit_url = 'http://localhost:15672/api'
    template = args.prefix + '.{} {} ' + str(int(time()))
    nodes_metrics = ['fd_used', 'fd_total', 'sockets_used', 'sockets_total',
                     'mem_used', 'mem_limit', 'disk_free', 'disk_free_limit',
                     'proc_used', 'proc_total', 'run_queue', 'processors']

    overview_object_totals_metrics = [
        'channels',
        'connections',
        'consumers',
        'exchanges',
        'queues',
    ]

    overview_queue_totals_metrics = [
        'messages',
        'messages_details.rate',
        'messages_ready',
        'messages_ready_details.rate',
        'messages_unacknowledged',
        'messages_unacknowledged_details.rate',
    ]

    overview_message_stats_metrics = [
        'ack',
        'ack_details.rate',
        'confirm',
        'confirm_details.rate',
        'deliver',
        'deliver_details.rate',
        'deliver_get',
        'deliver_get_details.rate',
        'deliver_no_ack',
        'deliver_no_ack_details.rate',
        'disk_reads',
        'disk_reads_details.rate',
        'disk_writes',
        'disk_writes_details.rate',
        'get',
        'get_details.rate',
        'get_no_ack',
        'get_no_ack_details.rate',
        'publish',
        'publish_details.rate',
        'redeliver',
        'redeliver_details.rate',
        'return_unroutable',
        'return_unroutable_details.rate',
    ]

    exchanges_message_stats_metrics = [
        'publish_in',
        'publish_in_details.rate',
        'publish_out',
        'publish_out_details.rate',
    ]

    # Overview data
    data = download(rabbit_url + '/overview')
    nodename = data['node']

    try:
        print(template.format(
            'statistics_db_event_queue', data['statistics_db_event_queue']
        ))
    except KeyError:
        pass

    for metric in overview_object_totals_metrics:
        try:
            print(template.format(
                'object_totals.' + metric, data['object_totals'][metric]
            ))
        except KeyError:
            pass
    for metric in overview_message_stats_metrics:
        try:
            if '.' in metric:
                print(template.format(
                    'message_stats.' + metric, get_metric_value(
                        metric.split('.'), data['message_stats'])
                ))
            else:
                print(template.format(
                    'message_stats.' + metric, data['message_stats'][metric]
                ))
        except KeyError:
            pass

    for metric in overview_queue_totals_metrics:
        try:
            if '.' in metric:
                print(template.format(
                    'queue_totals.' + metric, get_metric_value(
                        metric.split('.'), data['queue_totals'])
                ))
            else:
                print(template.format(
                    'queue_totals.' + metric, data['queue_totals'][metric]
                ))
        except KeyError:
                pass

    # Node data
    data = download(rabbit_url + '/nodes/' + nodename)

    for metric in nodes_metrics:
        try:
            print(template.format(metric, data[metric]))
        except KeyError:
            pass

    # Shovels data
    try:
        data = download(rabbit_url + '/shovels')
    except HTTPError:
        pass
    else:
        print(template.format('object_totals.shovels', str(len(data))))
        for shovel in data:
            state = 0
            if shovel['state'] == 'running':
                state = 1
            print(template.format('shovels.' + shovel['name'], state))

    # exchanges data
    try:
        data = download(rabbit_url + '/exchanges')
    except HTTPError:
        pass
    else:
        for exchange in data:
            for metric in exchanges_message_stats_metrics:
                if 'message_stats' in exchange:
                    if '.' in metric:
                        print(template.format(
                            'exchanges.{}.message_stats.{}'.format(
                                exchange['name'] if exchange['name'] else '0',
                                metric
                            ),
                            get_metric_value(
                                metric.split('.'),
                                exchange['message_stats']
                            )
                        ))
                    else:
                        print(template.format(
                            'exchanges.{}.message_stats.{}'.format(
                                exchange['name'] if exchange['name'] else '0',
                                metric
                            ),
                            exchange['message_stats'][metric]
                        ))


def get_metric_value(metric, data):
    """Get Metric value recursively for metric key from data"""

    if len(metric) > 1:
        return get_metric_value(metric[1:], data[metric[0]])

    return data[metric[0]]


def download(url):
    if sys.version_info.major == 3:
        base64string = base64.b64encode(b'guest:guest')
        headers = {
            'Authorization': 'Basic {0}'.format(base64string.decode('utf-8'))}
        req = Request(url, headers=headers)
        r = urlopen(req)
        return json.loads(r.readall().decode('utf-8'))
    else:
        base64string = base64.encodestring('%s:%s' % ('guest', 'guest'))[:-1]
        req = Request(url)
        req.add_header("Authorization", "Basic %s" % base64string)
        r = urlopen(req)
        return json.load(r)


if __name__ == '__main__':
    main()
