#!/usr/bin/env python
#
# igcollect - Fastly CDN
#
# Copyright (c) 2016, InnoGames GmbH
#

import sys
import json
import urllib2
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--to", dest="end_time", type=int, help="until when do you want to print the data")
parser.add_argument("-f", "--from", dest="start_time", type=int, help="start of the data printed")
parser.add_argument("-i", "--interval", dest="interval", choices=['minute','hour','day'], default='minute', help="interval the query should return the data in")
parser.add_argument("-s", "--service", dest="service", help="will only query the one service, if omitted all services will be queried")
parser.add_argument("-l", "--list", action="store_true", dest="show_list", help="Shows you available services")
parser.add_argument("-r", "--regions",  action="store_true", dest="regions", help="Shows you the currently available regions")
parser.add_argument("-k", "--key", dest="apikey", help="here you can provided the Fastly API Key this will replace one contained in the script")
args = parser.parse_args()

API_KEY=''
GRAPHITE_PREFIX = 'cdn.fastly'
if args.apikey: API_KEY=args.apikey

def get_data(fastly_url, api_header={"Fastly-Key": API_KEY}):
    req = urllib2.Request(url=fastly_url, headers=api_header)
    #print(time.time(),fastly_url)
    r=0
    f= None
    while f == None and r < 2:
        try:
            f = urllib2.urlopen(req, timeout = 1)
        except urllib2.URLError, e:
            #print("timeout")
            f = None
            r=r+1
    return json.loads(f.read())

def get_services():
    ''' query the services api and return a dictionary containing the
        service name and the service id'''
    service_data = get_data("https://api.fastly.com/service")
    all_services = {}
    for service in service_data:
        all_services[service['name']] = service['id']

    return all_services

def get_regions():
    ''' query the regions api and return a list of them '''
    try:
        regions = get_data("https://api.fastly.com/stats/regions")[u'data']
    except:
        # if the api is not available return a default set of regions
        return [u'africa', u'anzac', u'asia', u'europe', u'latam', u'usa']

    return regions

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

    # Always set the end time to now - 30 mintues to not get rate limted,
    # if you more recent data, you need to specify start and end time
    # using the -f and -t parameter
    now=int(time.time())
    endtime = now - 1900;

    # select reasonable default intervals for the query,
    # for a minutely interval we return an hours worth of data
    # for an hourly we return one day and
    # for a daily interval we'll retrun a months
    interval = args.interval
    if    interval == 'minute': starttime = now - 2500
    elif  interval == 'hour':   starttime = now - 88201
    elif  interval == 'day':    starttime = now - 2680201

    # use the provided start and end if present
    if args.end_time: endtime = args.end_time
    if args.start_time: starttime = args.start_time

    regions = get_regions()
    for service in all_services:
        for region in regions:
            try:
                stats_data = get_data("https://api.fastly.com/stats/service/%s?from=%s&to=%s&by=%s&region=%s" % (all_services[service], starttime , endtime, interval, region))
                for entry in stats_data['data']:
                    try:
                        # these values should be summarized by graphite using the average function later
                        for i in ['hit_ratio','hits_time','miss_time']:
                            print '%s.%s.%s.%s %s %s' % (GRAPHITE_PREFIX, service.replace(' ','_'), region ,  i,  str( float(entry[i]) ), str(entry['start_time']))

                        # these values contain an amount for an interval and therefore need to be summarized
                        # in graphite using the sum() function, in the default behavior this is done for all
                        # metrics ending in .count therefore we'll amend it here
                        for i in ['body_size','bandwidth','errors','header_size','hits','miss','pass','pipe','requests','status_1xx','status_200','status_204','status_2xx','status_301','status_302','status_304','status_3xx','status_4xx','status_503','status_5xx','uncacheable']:
                            print '%s.%s.%s.%s.count %s %s' % (GRAPHITE_PREFIX, service.replace(' ','_'), region,  i,  str( float(entry[i]) ), str(entry['start_time']))
                    except:
                        continue
            except:
                continue

if __name__ == "__main__":
    main()
