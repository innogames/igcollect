#!/usr/bin/env python
#
# igcollect - Fastly CDN
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function

import argparse
import json
import sys
import time
import urllib
import urllib2

import grequests

GRAPHITE_PREFIX = 'cdn.fastly'
FASTLY_BASE_URL = 'https://api.fastly.com'
AVG_KEYS = ('hit_ratio', 'hits_time', 'miss_time')
SUM_KEYS = (
    'body_size', 'bandwidth', 'errors', 'header_size', 'hits', 'miss', 'pass',
    'pipe', 'requests', 'status_1xx', 'status_200', 'status_204', 'status_2xx',
    'status_301', 'status_302', 'status_304', 'status_3xx', 'status_4xx',
    'status_503', 'status_5xx', 'uncacheable')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', dest='api_key', required=True,
                        help='here you can provided the Fastly API Key this '
                             'will replace one contained in the script')
    parser.add_argument('-s', '--service', dest='service',
                        help='will only query the one service, if omitted all '
                             'services will be queried')
    parser.add_argument('-t', '--to', dest='end_time', type=int,
                        help='until when do you want to print the data')
    parser.add_argument('-f', '--from', dest='start_time', type=int,
                        help='start of the data printed')
    parser.add_argument('-i', '--interval', dest='interval',
                        choices=['minute', 'hour', 'day'], default='minute',
                        help='interval the query should return the data in')
    parser.add_argument('-l', '--list', action='store_true', dest='show_list',
                        help='Shows you available services')
    parser.add_argument('-r', '--regions', action='store_true', dest='regions',
                        help='Shows you the currently available regions')
    return parser.parse_args()


def main(args):
    api_key = args.api_key
    if not api_key:
        print('you have to specify a api key with --key parameter')
        sys.exit(1)

    # Just show a list of possible services
    if args.show_list:
        all_services = get_services(api_key)
        for service_id, service_name in all_services.items():
            print('{}:{}'.format(service_name, service_id))
        sys.exit(0)

    # Query the API for all regions and print the list of them
    if args.regions:
        print(get_regions(api_key))
        sys.exit(0)

    # region Setting the from and to timestamps
    interval = args.interval
    now = int(time.time())

    # Always set the end time to now - 30 minutes to not get rate limited.
    # If you want more recent data, you need to specify start and end time
    # using the -f and -t parameters.
    if args.end_time:
        end_time = args.end_time
    else:
        end_time = now - 1800  # 30 * 60

    if args.start_time:
        start_time = args.start_time
    else:
        # Select reasonable default intervals for the query. For minutely
        # interval, we return hours worth of data; for hourly, we return
        # one day; and for a daily interval, we'll return a month (30 days).
        if interval == 'minute':
            start_time = now - 3600  # 60 * 60
        elif interval == 'hour':
            start_time = now - 86400  # 24 * 60 60
        elif interval == 'day':
            start_time = now - 3456000  # 30 * 24 * 60 * 60
        else:
            start_time = now - 3600
    # endregion Setting the from and to timestamps

    service = None
    if args.service:
        service = get_service_by_name(args.service, api_key)
        if not service:
            print('Unknown Service: {0:s}'.format(args.service))
            sys.exit(1)
        all_services = {service: args.service}
    else:
        all_services = get_services(api_key)

    string = GRAPHITE_PREFIX + '.{service}.{region}.{{value}}'
    regions = get_regions(api_key)

    responses = zip(
        regions,
        grequests.map((get_service_data_request(api_key, service, {
            'from': start_time, 'to': end_time,
            'by': interval, 'region': region,
        }) for region in regions), size=2)
    )

    for region, region_data in responses:
        if not region_data:
            print('NORESPONSE for region {:s}'.format(region), sys.stderr)
            continue

        region_data = region_data.json()
        if not region_data['data']:
            continue

        for service, data in region_data['data'].items():
            if service not in all_services:
                continue

            service_name = all_services[service]
            service_name = service_name.replace(' ', '_')
            output = string.format(service=service_name, region=region)

            for entry in data:
                for key in entry:
                    value = format_key(entry, key)
                    if not value:
                        continue
                    print(output.format(value=value))


def get_service_data_request(api_key, service=None, query=None):
    if not service:
        url = '/stats'
    else:
        url = '/stats/service/{s}'.format(s=service)
    return grequests.get(FASTLY_BASE_URL + url, headers={"Fastly-Key": api_key},
                         params=query)


def get_service_data(api_key, service=None, query=None):
    query = urllib.urlencode(query)

    if not service:
        url = '/stats?' + query
        services_data = get_data(url, api_key)['data']
    else:
        url = '/stats/service/{s}?{q}'.format(s=service, q=query)
        services_data = {service: get_data(url, api_key)['data']}

    return {service_id: data for service_id, data in services_data.items()}


def get_services(api_key):
    """Query the services API"""
    service_data = get_data('/service', api_key)
    return {s['id']: s['name'] for s in service_data}


def get_service_by_name(name, api_key):
    """Search for a service by name"""
    service_info = get_data('/service/search?name={:s}'.format(name), api_key)
    if service_info:
        return service_info['id']


def get_regions(api_key):
    """Query the regions API"""
    return get_data('/stats/regions', api_key)['data']


def get_data(fastly_url, api_key):
    url = FASTLY_BASE_URL + fastly_url
    req = urllib2.Request(url=url, headers={'Fastly-Key': api_key})
    fd = urllib2.urlopen(req, timeout=10)
    return json.loads(fd.read())


def format_key(entry, key):
    template = '{key}{count} {value} {start_time}'

    # These values should be summarized by graphite using the
    # average function later
    if key in AVG_KEYS:
        return template.format(key=key, count='',
                               value=float(entry[key]),
                               start_time=entry['start_time'])

    # These values contain an amount for an interval and
    # therefore need to be summarized in graphite using the
    # sum() function, in the default behavior this is done for
    # all metrics ending in .count therefore we'll amend it
    # here.
    if key in SUM_KEYS:
        return template.format(key=key, count='.count',
                               value=float(entry[key]),
                               start_time=entry['start_time'])


if __name__ == '__main__':
    main(parse_args())
