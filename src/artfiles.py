#!/usr/bin/env python
#
# igcollect - Artfiles hosting
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time
from urllib import urlopen


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
    artfiles_url = (
        'https://{}:{}@dcp.c.artfiles.de/api/stats/get_estats.html'
        .format(args.http_user, args.http_pass)
    )
    data = urlopen(artfiles_url)
    template = args.prefix + '.{}.{}.{}.{} {} ' + str(int(time()))
    for csv in data.readlines():
        if csv.startswith('"level3"') or csv.startswith('"w408'):
            parse_and_print(template, csv)


def parse_and_print(template, csv):
    values = [v.strip('\n "') for v in csv.split(',')]
    dc = values[0].replace('/', '_')
    rack = values[1].translate(None, '/')
    pdu_nr = values[2]
    maxcur = values[3]
    measurement_type = values[4]
    maxval_watt = values[5]
    curval = values[6]

    if maxcur == '10A':
        print(template.format(dc, rack, pdu_nr, 'max', '10.00'))
    elif maxcur == '16A':
        print(template.format(dc, rack, pdu_nr, 'max', '16.00'))
    elif maxcur == 'redundant':
        print(template.format(dc, rack, pdu_nr, 'max', '20.00'))

    if measurement_type == 'ampere':
        ampere = curval.translate(None, ' A')
        print(template.format(dc, rack, pdu_nr, 'ampre', ampere))

    if measurement_type == 'kwh':
        kwh = maxval_watt.translate(None, ' kWh')
        print(template.format(dc, rack, pdu_nr, 'kwh', kwh))


if __name__ == '__main__':
    main()
