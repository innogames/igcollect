#!/usr/bin/env python
#
# igcollect - Artfiles hosting
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
import sys
import urllib
import argparse
from socket import gethostname

parser = argparse.ArgumentParser()
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
args = parser.parse_args()


artfiles_url = 'https://%s:%s@dcp.c.artfiles.de/api/stats/get_estats.html' % (
    args.http_user, args.http_pass)
data = urllib.urlopen(artfiles_url)
csv = data.readlines()

now = str(int(time.time()))

graphite = ""
for line in csv:
    if line.startswith('"level3"') or line.startswith('"w408'):
        dc, rack, pdu_nr, maxcur, measurementtype, maxval_watt, curval = line.split(
            ',')
        dc = dc.strip('"').replace('/', '_')
        rack = rack.strip('"').translate(None, '/')
        pdu_nr = pdu_nr.strip('"')

        if maxcur == '"16A"':
            graphite += 'powerline.' + dc + '.' + rack + '.' + \
                pdu_nr + '.max ' + '16.00 ' + str(now) + '\n'
        elif maxcur == '"10A"':
            graphite += 'powerline.' + dc + '.' + rack + '.' + \
                pdu_nr + '.max ' + '10.00 ' + str(now) + '\n'
        elif maxcur == '"redundant"':
            graphite += 'powerline.' + dc + '.' + rack + '.' + \
                pdu_nr + '.max ' + '20.00 ' + str(now) + '\n'

        if measurementtype == '"ampere"':
            ampere = curval.translate(None, '" A\n')
            graphite += 'powerline.' + dc + '.' + rack + '.' + \
                pdu_nr + '.ampre ' + str(ampere) + ' ' + str(now) + '\n'
        if measurementtype == '"kwh"':
            kwh = maxval_watt.translate(None, '" kWh\n')
            graphite += 'powerline.' + dc + '.' + rack + '.' + \
                pdu_nr + '.kwh ' + str(kwh) + ' ' + str(now) + '\n'

print graphite
