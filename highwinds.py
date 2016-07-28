#!/usr/bin/env python
#
# igcollect - Highwinds CDN
#
# Copyright (c) 2016, InnoGames GmbH
#

import json
import sys
import time
import urllib
import urllib2
from argparse import ArgumentParser

import grequests

GRAPHITE_PREFIX = 'cdn.highwinds'
HIGHWINDS_BASE_URL = 'https://striketracker.highwinds.com/api/v1'
AVG_KEYS = ('xferRateMeanMbps', 'xferRateMbps', 'userXferRateMbps', 'rps',
            'completionRatio')
SUM_KEYS = ('xferUsedTotalMB', 'requestsCountTotal', 'responseSizeMeanMB')
PLATFORMS = ('cds', 'sds', 'cdi', 'sdi')


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-t", "--to", dest="end_time", type=int,
                        help="until when do you want to print the data")
    parser.add_argument("-f", "--from", dest="start_time", type=int,
                        help="start of the data printed")
    parser.add_argument("-i", "--interval", dest="interval",
                        choices=['PT5M', 'PT1H', 'P1M', 'P1D'], default='PT5M',
                        help="interval the query should return the data in")
    parser.add_argument("--filter-hosts", dest="filter_hosts",
                        help="will only query the one host, if omitted all "
                             "hosts will be queried")
    parser.add_argument("-l", "--list", action="store_true", dest="show_list",
                        help="Shows you available hosts")
    parser.add_argument("-r", "--regions", action="store_true", dest="regions",
                        help="Shows you the currently available regions")
    parser.add_argument("-a", "--account-hash", dest="account_hash",
                        required=True,
                        help="here you can provied the highwinds account hash "
                             "this will replace one contained in the script")
    parser.add_argument("-k", "--key", dest="api_key", required=True,
                        help="here you can provied the highwinds API Key this "
                             "will replace one contained in the script")
    return parser.parse_args()


def main(args):
    api_key = args.api_key
    account_hash = args.account_hash

    if not api_key or not account_hash:
        print('you have to specify an api key and account hash with --key '
              'resp. --account-hash parameter')
        sys.exit(1)

    # Just show a list of possible hosts
    if args.show_list:
        all_hosts = get_hosts(account_hash, api_key)
        for host_id, host_name in all_hosts.items():
            print('{}:{}'.format(host_name, host_id))
        sys.exit(0)

    # Query the API for all regions and print the list of them
    if args.regions:
        print(get_regions(api_key))
        sys.exit(0)

    if args.filter_hosts:
        hosts = get_hosts_by_name(args.filter_hosts, account_hash, api_key)
        if not hosts:
            print('Unknown Host: {0:s}'.format(args.filter_hosts))
            sys.exit(1)
        all_hosts = hosts
    else:
        all_hosts = get_hosts(account_hash, api_key)

    # Always set the end time to now - 30 minutes to not get rate limited,
    # if you more recent data, you need to specify start and end time
    # using the -f and -t parameter
    now = time.time()
    if args.end_time:
        end_time = args.end_time
    else:
        end_time = now - 1800

    # select reasonable default intervals for the query,
    # for a minutely interval we return an hours worth of data
    # for an hourly we return one day and
    # for a daily interval we'll return a month
    interval = args.interval

    # use the provided start if present
    if args.start_time:
        start_time = args.start_time
    else:
        if interval == 'PT5M':
            start_time = end_time - 3600
        elif interval == 'PT1H':
            start_time = end_time - 86400
        elif interval == 'P1D':
            start_time = end_time - 2678400
        else:
            start_time = end_time - 3600  # minutely interval is default

    start_time = get_date_and_time(start_time)
    end_time = get_date_and_time(end_time)

    pairs = [
        (region, platform)
        for region in get_regions(api_key)
        for platform in PLATFORMS
        ]

    responses = zip(
        pairs,
        grequests.map(get_host_data_request(account_hash, api_key, {
            'startDate': start_time, 'endDate': end_time,
            'granularity': interval, 'platforms': platform,
            'billingRegions': region, 'groupBy': 'HOST',
        }) for region, platform in pairs)
    )

    for (region, platform), response in responses:
        stats_series = response.json()['series']
        for stats_host in stats_series:
            host_id = stats_host['key']
            if host_id not in all_hosts:
                continue

            if not stats_host['data']:
                continue

            host_name = (all_hosts[host_id]
                         .replace(' ', '_')
                         .replace('.', '_'))

            stats = (dict(zip(stats_host['metrics'], d)) for d in
                     stats_host['data'])

            for stat in stats:
                timestamp = int(int(stat['usageTime']) / 1000)
                for value in AVG_KEYS:
                    print("%s.%s.%s.%s.%s %f %s" % (
                        GRAPHITE_PREFIX, host_name, platform,
                        region, value, stat[value],
                        timestamp))

                for value in SUM_KEYS:
                    print("%s.%s.%s.%s.%s.count %f %s" % (
                        GRAPHITE_PREFIX, host_name, platform,
                        region, value, stat[value],
                        timestamp))


def get_host_data_request(account_hash, api_key, query={}):
    url = '/accounts/{account_hash}/analytics/transfer'.format(
        account_hash=account_hash)
    return get_data_request(url, api_key, query)


def get_host_data(account_hash, api_key, query={}):
    query = urllib.urlencode(query)
    url = '/accounts/{account_hash}/analytics/transfer?{query}'.format(
        account_hash=account_hash, query=query)
    hosts_data = get_data(url, api_key)['series']
    return hosts_data


def get_data_request(highwinds_url, api_key, params={}):
    return grequests.get(HIGHWINDS_BASE_URL + highwinds_url,
                         headers={"Authorization": 'Bearer {}'.format(
                             api_key)}, params=params)


def get_data(highwinds_url, api_key):
    req = urllib2.Request(
        url=HIGHWINDS_BASE_URL + highwinds_url,
        headers={"Authorization": 'Bearer {}'.format(api_key)},
    )
    f = urllib2.urlopen(req)
    return json.loads(f.read())


def get_hosts(account_hash, api_key):
    """ query the hosts api and return a dictionary containing the
        host name and the host id"""
    host_data = get_data("/accounts/" + account_hash + "/hosts", api_key)
    return {h['hashCode']: h['name'] for h in host_data['list']}


def get_hosts_by_name(host_name, account_hash, api_key):
    url = '/accounts/{:s}/search?search={:s}'.format(account_hash, host_name)
    hosts = get_data(url, api_key)['hosts']
    return {h['hostHash']: h['name'] for h in hosts}


def get_regions(api_key):
    """ query the regions api and return a list of them """
    region_data = get_data("/billingRegions", api_key)['list']
    return [r['code'] for r in region_data]


def get_date_and_time(seconds=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


if __name__ == "__main__":
    main(parse_args())
