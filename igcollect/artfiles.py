#!/usr/bin/env python
"""igcollect - Artfiles Hosting Metrics

Copyright (c) 2019 InnoGames GmbH
"""

import base64
from argparse import ArgumentParser
from time import time

try:
    # Try importing the Python3 packages
    from urllib.request import Request, urlopen
except ImportError:
    # On failure, import the Python2
    from urllib2 import Request, urlopen


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='artfiles')
    parser.add_argument(
        "-u",
        "--user",
        dest="http_user",
        type=str,
        required=True,
        help="the http user name to authenticate")
    parser.add_argument(
        "-p",
        "--pass",
        dest="http_pass",
        type=str,
        required=True,
        help="the http password to authenticate")
    return parser.parse_args()


def main():
    args = parse_args()
    request = Request('https://dcp.c.artfiles.de/api/stats/get_estats.html')
    credentials = '{}:{}'.format(args.http_user, args.http_pass)
    base64credentials = base64.b64encode(credentials.encode())
    request.add_header('Authorization',
                       'Basic {}'.format(base64credentials.decode()))
    data = urlopen(request)
    template = args.prefix + '.{dc}.{rack}.{pdu_nr}.{unit} {value} ' + str(
        int(time()))
    for csv in data.readlines():
        csv = csv.decode()
        if csv.startswith('"level3"') or csv.startswith('"w408'):
            parse_and_print(template, csv)


def parse_and_print(template, csv):
    values = [v.strip('\n "') for v in csv.split(',')]
    dc = values[0].replace('/', '_')
    rack = values[1].replace('/', '')
    pdu_nr = values[2]
    maxcur = values[3]
    measurement_type = values[4]
    maxval_watt = values[5]
    curval = values[6]

    if maxcur == '10A':
        print(template.format(dc=dc, rack=rack, pdu_nr=pdu_nr, unit='max',
                              value='10.00'))
    elif maxcur == '16A':
        print(template.format(dc=dc, rack=rack, pdu_nr=pdu_nr, unit='max',
                              value='16.00'))
    elif maxcur == '32A':
        print(template.format(dc=dc, rack=rack, pdu_nr=pdu_nr, unit='max',
                              value='32.00'))
    elif maxcur == 'redundant':
        print(template.format(dc=dc, rack=rack, pdu_nr=pdu_nr, unit='max',
                              value='20.00'))

    # only for kwh racks we get the total
    if measurement_type == 'kwh':
        kwh = maxval_watt.replace(' kWh', '')
        print(template.format(dc=dc, rack=rack, pdu_nr=pdu_nr, unit='kwh',
                              value=kwh))

    # we now always get the current
    ampere = curval.replace(' A', '')
    print(template.format(dc=dc, rack=rack, pdu_nr=pdu_nr, unit='ampere',
                          value=ampere))


if __name__ == '__main__':
    main()
