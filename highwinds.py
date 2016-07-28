#!/usr/bin/env python
#
# igcollect - Highwinds CDN
#
# Copyright (c) 2016, InnoGames GmbH
#

import sys
import json
import urllib2
import argparse
import time

GRAPHITE_PREFIX = 'cdn.highwinds'
HIGHWINDS_BASE_URL = 'https://striketracker.highwinds.com/api/v1'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--to", dest="end_time", type=int,
                        help="until when do you want to print the data")
    parser.add_argument("-f", "--from", dest="start_time", type=int,
                        help="start of the data printed")
    parser.add_argument("-i", "--interval", dest="interval",
                        choices=['PT5M', 'PT1H', 'P1M', 'P1D'], default='PT5M',
                        help="interval the query should return the data in")
    parser.add_argument("-s", "--service", dest="service",
                        help="will only query the one service, if omitted all "
                             "services will be queried")
    parser.add_argument("-l", "--list", action="store_true", dest="show_list",
                        help="Shows you available services")
    parser.add_argument("-r", "--regions", action="store_true", dest="regions",
                        help="Shows you the currently available regions")
    parser.add_argument("-a", "--accounthash", dest="account_hash",
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
              'resp. --accounthash parameter')
        sys.exit(1)

    # You will need at least python2.7
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
        sys.stderr.write("at least python2.7 is required\n")
        sys.exit(1)

    # Just show a list of possible services
    if args.show_list:
        all_services = get_services(api_key)
        for service in all_services:
            print(service)
        sys.exit(0)

    # Query the API for all regions and print the list of them
    if args.regions:
        print(get_regions(api_key))
        sys.exit(0)

    all_services = get_services(account_hash, api_key)
    if args.service:
        try:
            all_services = {args.service: all_services[args.service]}
        except:
            print("unknown service: %s" % args.service)
            sys.exit(1)

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
    if interval == 'PT5M':
        start_time = end_time - 3600
    elif interval == 'PT1H':
        start_time = end_time - 86400
    elif interval == 'P1D':
        start_time = end_time - 2680201
    else:
        start_time = end_time - 3600  # minutely interval is default

    # use the provided start if present
    if args.start_time:
        start_time = args.start_time

    for service in all_services:
        service_escaped = service.replace(' ', '_').replace('.', '_')
        for region in get_regions(api_key):
            for service_type in ['cds', 'sds', 'cdi', 'sdi']:
                try:
                    url = "/accounts/%s/analytics/transfer?startDate=%s&endDate=%s&granularity=%s&platforms=%s&pops=&billingRegions=%s&accounts=&hosts=%s&groupBy=HOST" % (
                        account_hash, get_date_and_time(start_time),
                        get_date_and_time(end_time), interval, service_type,
                        region,
                        all_services[service])

                    stats_data = get_data(url, api_key)

                    metrics = stats_data[u'series'][0][u'metrics']
                    data = stats_data[u'series'][0][u'data']
                    stats = []

                    for i in data:
                        stats.append(dict((zip(metrics, i))))

                    for i in stats:
                        timestamp = int(int(i[u'usageTime']) / 1000)
                        for value in [u'xferRateMeanMbps', u'xferRateMbps',
                                      u'userXferRateMbps', u'rps',
                                      u'completionRatio']:
                            print("%s.%s.%s.%s.%s %f %s" % (
                                GRAPHITE_PREFIX, service_escaped, service_type,
                                region, str(value), float(i[value]),
                                str(timestamp)))

                        for value in [u'xferUsedTotalMB', u'requestsCountTotal',
                                      u'responseSizeMeanMB']:
                            print("%s.%s.%s.%s.%s.count %f %s" % (
                                GRAPHITE_PREFIX, service_escaped, service_type,
                                region, str(value), float(i[value]),
                                str(timestamp)))
                except:
                    continue


def get_data(highwinds_url, api_key):
    req = urllib2.Request(
        url=HIGHWINDS_BASE_URL + highwinds_url,
        headers={"Authorization": 'Bearer {}'.format(api_key)},
    )
    f = urllib2.urlopen(req)
    return json.loads(f.read())


def get_services(account_hash, api_key):
    """ query the services api and return a dictionary containing the
        service name and the service id"""
    service_data = get_data("/accounts/" + account_hash +
                            "/hosts?recursive=&categories=", api_key)
    all_services = {}
    for service in service_data[u'list']:
        all_services[service['name']] = service['hashCode']

    return all_services


def get_regions(api_key):
    """ query the regions api and return a list of them """
    try:
        regions = []
        for i in get_data("/billingRegions", api_key)[u'list']:
            regions.append(i['code'])
    except:
        # if the api is not available return a default set of regions
        return [u'oc', u'us', u'sa', u'as']

    return regions


def get_date_and_time(seconds=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


if __name__ == "__main__":
    main(parse_args())
