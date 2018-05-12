#!/usr/bin/env python
"""igcollect - Artfiles Uplink Traffic

Copyright (c) 2017 InnoGames GmbH
"""

import logging
from argparse import ArgumentParser
from datetime import datetime, timedelta
from time import mktime

import grequests
import requests
from requests.auth import HTTPBasicAuth


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='artfiles-uplink')
    parser.add_argument('-u', '--user', dest='username',
                        help='The http username to authenticate.')
    parser.add_argument('-p', '--pass', dest='password',
                        help='The http password to authenticate.')
    parser.add_argument('-m', '--minutes', type=int,
                        help='Just data from theis amount of minutes back in '
                             'time will be printed')
    parser.add_argument('-s', '--switches', nargs='*',
                        help='Just print data from these switches '
                             '(api id of the switches)')
    parser.add_argument('-v', '--verbose', action='count',
                        help='Verbose mode as counter '
                             '(1: info, 2: debug, ...)')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        logging.basicConfig(level=(3 - args.verbose) * 10)
    else:
        logging.disable(logging.CRITICAL)

    logger = logging.getLogger('artfiles_uplink_traffic')

    filter_func = None
    if args.minutes:
        time_from = datetime.now() - timedelta(minutes=args.minutes)
        logger.debug(time_from)
        time_from = mktime(time_from.timetuple())
        logger.debug(time_from)

        def filter_func(timestamp):
            return timestamp >= time_from

    auth = None
    if args.username:
        auth = HTTPBasicAuth(args.username, args.password)

    switches = get_switches(auth)
    logger.info(switches)
    if args.switches:
        switches = [switch for switch in switches
                    if switch['id'] in args.switches]

    stat_requests = [
        get_traffic_stat_request(switch['id'], base=1, auth=auth)
        for switch in switches
        ]
    for request in stat_requests:
        logger.info(request.__dict__)

    responses = grequests.map(stat_requests)

    responses = zip(switches, responses)

    template = '{prefix}.{title}.{port}.{metric} {value} {time}'
    factors = {'Tbps': 1000000000000, 'Gbps': 1000000000, 'Mbps': 1000000,
               'Kbps': 1000, 'bps': 1}
    for switch, response in responses:
        if not response:
            logger.debug('No response: {}'.format(response.url))
            continue

        try:
            json_data = response.json()
        except ValueError as e:
            logger.warning('Error: %s', e)
            logger.warning('Strange Response:')
            logger.warning('URL: %s', response.url)
            logger.warning('Content:\n%s', response.content)
            continue

        logger.info(json_data)

        title = switch['switch'].replace('.', '_')
        port = switch['port'].replace(':', '_')

        template_params = {'prefix': args.prefix, 'title': title, 'port': port}

        parse_and_print_data(json_data.get('input'), 'bpsIn', factors,
                             filter_func, template, template_params)

        parse_and_print_data(json_data.get('output'), 'bpsOut', factors,
                             filter_func, template, template_params)


def get_switches(auth):
    scheme = 'https'
    host = 'dcp.c.artfiles.de'
    endpoint = 'api/stats/get_traffic.html'
    url = ('{scheme}://{host}/{endpoint}'
           .format(scheme=scheme, host=host, endpoint=endpoint))
    response = requests.get(url, auth=auth)

    return response.json()


def get_traffic_stat_request(switch_id, base=None, auth=None):
    scheme = 'https'
    host = 'dcp.c.artfiles.de'
    endpoint = 'api/stats/get_traffic.html'
    url = ('{scheme}://{host}/{endpoint}'
           .format(scheme=scheme, host=host, endpoint=endpoint))
    query = {'id': switch_id, 'si_base': base}
    request = grequests.get(url, params=query, auth=auth)

    return request


def parse_and_print_data(data, metric, factors=None, filter=None,
                         template=None, template_params=None):
    if template_params is None:
        template_params = {}

    if not factors:
        factors = {'Tbps': 1000000000000, 'Gbps': 1000000000, 'Mbps': 1000000,
                   'Kbps': 1000, 'Bps': 1}

    factor = parse_factor(
        data.get('meta').get('yValueFormatString'),
        factors
    )
    for traffic in data.get('data'):
        timestamp = int(traffic.get('x') / 1000)

        if not filter(timestamp):
            continue

        value = abs(traffic.get('y')) * factor
        print(template.format(
            metric=metric, value=value, time=timestamp, **template_params)
        )


def parse_factor(factor_string, factor_table):
    template, factor = factor_string.split()

    return factor_table.get(factor)


if __name__ == '__main__':
    main()
