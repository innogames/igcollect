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
import os

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--to", dest="end_time", type=int, help="until when do you want to print the data")
parser.add_argument("-f", "--from", dest="start_time", type=int, help="start of the data printed")
parser.add_argument("-i", "--interval", dest="interval", choices=['PT5M','PT1H','P1M','P1D'], default='PT5M', help="interval the query should return the data in")
parser.add_argument("-s", "--service", dest="service", help="will only query the one service, if omitted all services will be queried")
parser.add_argument("-l", "--list", action="store_true", dest="show_list", help="Shows you available services")
parser.add_argument("-r", "--regions",  action="store_true", dest="regions", help="Shows you the currently available regions")
parser.add_argument("-a", "--accounthash", dest="accounthash", help="here you can provied the highwinds account hash this will replace one contained in the script")
parser.add_argument("-k", "--key", dest="apikey", help="here you can provied the highwinds API Key this will replace one contained in the script")
args = parser.parse_args()

API_KEY='Bearer '
ACCOUNT_HASH=''
GRAPHITE_PREFIX = 'cdn.highwinds'
if args.apikey: API_KEY = 'Bearer ' + args.apikey
if args.accounthash: ACCOUNT_HASH = args.accounthash

def get_data(highwinds_url, api_header={"Authorization": API_KEY}):
    req = urllib2.Request(url=highwinds_url, headers=api_header)
    f = urllib2.urlopen(req)
    return json.loads(f.read())

def get_services():
    ''' query the services api and return a dictionary containing the
        service name and the service id'''
    service_data = get_data("https://striketracker.highwinds.com/api/v1/accounts/" + ACCOUNT_HASH + "/hosts?recursive=&categories=")
    all_services = {}
    for service in service_data[u'list']:
        all_services[service['name']] = service['hashCode']

    return all_services

def get_regions():
    ''' query the regions api and return a list of them '''
    try:
        regions = []
        for i in get_data("https://striketracker.highwinds.com/api/v1/billingRegions")[u'list']:
            regions.append(i['code'])
    except:
        # if the api is not available return a default set of regions
        return [u'oc', u'us', u'sa', u'as']

    return regions

def getDateAndTime(seconds=None):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))

def main():
    #You will need at least python2.7
    if sys.version_info[0] == 2 and sys.version_info[1] < 7:
       sys.stderr.write("at least python2.7 is required\n")
       sys.exit(1)

    #Just show a list of possible services
    if args.show_list:
        all_services = get_services()
        for service in all_services:
            print(service)
        sys.exit(0)

    #Query the API for all regions and print the list of them
    if args.regions:
        print(get_regions())
        sys.exit(0)

    all_services = get_services()
    if args.service:
        try:
            all_services = {args.service: all_services[args.service]}
        except:
            print("unknown service: %s" % args.service)
            sys.exit(1)

    # Always set the end time to now - 30 minutes to not get rate limited,
    # if you more recent data, you need to specify start and end time
    # using the -f and -t parameter
    now=time.time()
    endtime = now - 900;

    # select reasonable default intervals for the query,
    # for a minutely interval we return an hours worth of data
    # for an hourly we return one day and
    # for a daily interval we'll return a month
    interval = args.interval
    if    interval == 'PT5M':   starttime = endtime - 3600
    elif  interval == 'PT1H':   starttime = endtime - 86400
    elif  interval == 'P1D':    starttime = endtime - 2680201

    # use the provided start and end if present
    if args.end_time: endtime = args.end_time
    if args.start_time: starttime = args.start_time

    for service in all_services:
        service_escaped = service.replace(' ','_').replace('.','_')
        for region in get_regions():
            for service_type in ['cds', 'sds', 'cdi', 'sdi']:
                try:
                    url = "https://striketracker.highwinds.com/api/v1/accounts/%s/analytics/transfer?startDate=%s&endDate=%s&granularity=%s&platforms=%s&pops=&billingRegions=%s&accounts=&hosts=%s&groupBy=HOST" % (ACCOUNT_HASH, getDateAndTime(starttime), getDateAndTime(endtime), interval, service_type, region, all_services[service])

                    stats_data = get_data(url)

                    metrics = stats_data[u'series'][0][u'metrics']
                    data =  stats_data[u'series'][0][u'data']
                    stats = []

                    for i in data:
                        stats.append(dict((zip(metrics,i))))

                    for i in stats:
                        timestamp = int(int(i[u'usageTime'])/1000)
                        for value in [u'xferRateMeanMbps', u'xferRateMbps', u'userXferRateMbps', u'rps', u'completionRatio']:
                            print("%s.%s.%s.%s.%s %f %s" % (GRAPHITE_PREFIX, service_escaped, service_type, region ,str(value), float(i[value]), str(timestamp) ))

                        for value in [u'xferUsedTotalMB', u'requestsCountTotal', u'responseSizeMeanMB' ]:
                            print("%s.%s.%s.%s.%s.count %f %s" % (GRAPHITE_PREFIX, service_escaped, service_type, region ,str(value), float(i[value]), str(timestamp)  ))
                except:
                    continue

if __name__ == "__main__":
    main()
