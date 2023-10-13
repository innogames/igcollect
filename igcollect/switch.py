#!/usr/bin/env python3
"""igcollect - Switch

This script collects

* port traffic
* port errors
* CPU utilization
* SFP Digital Optical Monitoring metrics

from a switch via SNMP.

Copyright (c) 2017 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time
from pysnmp import error
import re
import sys

from snmp import (
    get_snmp_connection,
    get_snmp_value,
    get_snmp_table,
    IgCollectSNMPException,
)

# Predefine some variables, it makes this program run a bit faster.

OIDS = {
    'switch_model': '1.3.6.1.2.1.1.1.0',
    'port_name': '1.3.6.1.2.1.31.1.1.1.1',
    'port_state': '1.3.6.1.2.1.2.2.1.8',
}

LAGG_OIDS = {
    'procurve': '.1.3.6.1.4.1.11.2.14.11.5.1.7.1.3.1.1.8',
    'powerconnect': '1.2.840.10006.300.43.1.2.1.1.12',
}

CPU_OIDS = {
    'procurve': '1.3.6.1.4.1.11.2.14.11.5.1.9.6.1.0',
    'powerconnect': '1.3.6.1.4.1.674.10895.5000.2.6132.1.1.1.1.4.9.0',
    'extreme': '1.3.6.1.4.1.1916.1.32.1.2.0',
    # 1-minute average for the 1st cpu of stack because we don't stack them.
    'force10_mxl': '1.3.6.1.4.1.6027.3.26.1.4.4.1.4.2.1.1',
    'cisco_ios': '1.3.6.1.4.1.9.9.109.1.1.1.1.4.1',
    'netiron_mlx': '1.3.6.1.4.1.1991.1.1.2.11.1.1.5.1.1.1',
    'cumulus': '1.3.6.1.4.1.2021.11.11.0',
    'edgeswitch': '.1.3.6.1.4.1.4413.1.1.1.1.4.8.1.3.0',
}

DOM_OIDS = {
    'force10_mxl': {
        'bias_current.0': '1.3.6.1.4.1.6027.3.11.1.3.1.1.18',
        'bias_current.1': '1.3.6.1.4.1.6027.3.11.1.3.1.1.19',
        'bias_current.2': '1.3.6.1.4.1.6027.3.11.1.3.1.1.20',
        'bias_current.3': '1.3.6.1.4.1.6027.3.11.1.3.1.1.21',
        'rx_power.0': '1.3.6.1.4.1.6027.3.11.1.3.1.1.12',
        'rx_power.1': '1.3.6.1.4.1.6027.3.11.1.3.1.1.13',
        'rx_power.2': '1.3.6.1.4.1.6027.3.11.1.3.1.1.14',
        'rx_power.3': '1.3.6.1.4.1.6027.3.11.1.3.1.1.15',
        'sfp_voltage': '1.3.6.1.4.1.6027.3.11.1.3.1.1.17',
        'temperature': '1.3.6.1.4.1.6027.3.11.1.3.1.1.16',
        'tx_power.0': '1.3.6.1.4.1.6027.3.11.1.3.1.1.8',
        'tx_power.1': '1.3.6.1.4.1.6027.3.11.1.3.1.1.9',
        'tx_power.2': '1.3.6.1.4.1.6027.3.11.1.3.1.1.10',
        'tx_power.3': '1.3.6.1.4.1.6027.3.11.1.3.1.1.11',
    }
}

COUNTERS = {
    'bytesIn': '1.3.6.1.2.1.31.1.1.1.6',
    'bytesOut': '1.3.6.1.2.1.31.1.1.1.10',
    'pktsIn': '1.3.6.1.2.1.31.1.1.1.7',
    'pktsOut': '1.3.6.1.2.1.31.1.1.1.11',
    'brdPktsIn': '1.3.6.1.2.1.31.1.1.1.9',
    'brdPktsOut': '1.3.6.1.2.1.31.1.1.1.13',
    'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
    'ifOutErrors': '1.3.6.1.2.1.2.2.1.20',
    'ifInDiscards': '1.3.6.1.2.1.2.2.1.13',
    'ifOutDiscards': '1.3.6.1.2.1.2.2.1.19',
}

COUNTERS_IGNORE = {
    'force10_mxl': {
        # This counter is required to distinguish packets discarded due to port
        # being disabled by STP from other types of discarded packets.
        # Due to nature of couters this will never reach exact 0.
        # Of course it would be way better to totally ignore counters of ports
        # blocked by STP but I can't find such information in any MIB.
        'ifInDiscards': '1.3.6.1.4.1.6027.3.27.1.3.1.3',
    },
}

PORT_REGEXP = {
    'cisco_ios': re.compile('^(?P<port>(Fa|Gi|Tu)[0-9/]+)$'),
    'cumulus': re.compile('^(?P<port>swp[0-9]+(s[0-9]+)?)$'),
    'extreme': re.compile('^(?P<port>[0-9]:[0-9]+)$'),
    'force10_mxl': re.compile(
        '^(TenGigabitEthernet|fortyGigE) (?P<port>[0-9]+/[0-9]+)$'
    ),
    'netiron_mlx': re.compile('^(?P<port>ethernet[0-9]+/[0-9]+)$'),
    'powerconnect': re.compile('^(?P<port>(Gi|Te|Po|Trk)[0-9/]+)$'),
    'procurve': re.compile('^(?P<port>[0-9]+)$'),
    'edgeswitch': re.compile('^(?P<port>[0-9]+/[0-9]+)'),
}


class SwitchException(Exception):
    pass


def main():
    args = parse_args()
    if not args.prefix:
        args.prefix = 'switches.{}'.format(args.switch)
    try:
        snmp = get_snmp_connection(args)
    except error.PySnmpError as e:
        print(e, file=sys.stderr)
        return -1

    try:
        model = get_switch_model(snmp)
    except SwitchException as e:
        print(e, file=sys.stderr)
        return -1

    if not model:
        return -1

    cpu_stats(args.prefix, snmp, model)
    monitored_ports = get_monitored_ports(snmp, model)
    ports_stats(args.prefix, snmp, monitored_ports, model)

    # We check DOM metrics only for switch models that have OIDs added to
    # the script
    if model in DOM_OIDS:
        dom_stats(args.prefix, snmp, monitored_ports, DOM_OIDS[model])


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('host', type=str, help='Hostname of a switch')
    parser.add_argument('--prefix', help='Graphite prefix')

    snmp_mode = parser.add_mutually_exclusive_group(required=True)
    snmp_mode.add_argument('--community', help='SNMP community')
    snmp_mode.add_argument('--user', help='SNMPv3 user')

    parser.add_argument('--auth', help='SNMPv3 authentication key')
    parser.add_argument('--priv', help='SNMPv3 privacy key')
    parser.add_argument(
        '--priv_proto',
        help='SNMPv3 privacy protocol: aes (default) or des',
        default='aes'
    )
    return parser.parse_args()


def get_switch_model(snmp):
    """ Recognize model of switch from SNMP MIB-2 sysDescr """

    model = get_snmp_value(snmp, OIDS['switch_model'])

    if 'PowerConnect' in model:
        return 'powerconnect'
    elif 'ProCurve' in model:
        return 'procurve'
    elif 'Aruba' in model:
        return 'procurve'
    elif 'ExtremeXOS' in model:
        return 'extreme'
    elif 'Dell Networking OS' in model:
        return 'force10_mxl'
    elif 'Cisco IOS Software' in model:
        return 'cisco_ios'
    elif 'Brocade NetIron MLX' in model:
        return 'netiron_mlx'
    elif 'Cumulus-Linux' in model:
        return 'cumulus'
    elif 'EdgeSwitch' in model:
        return 'edgeswitch'

    raise SwitchException(f'Unknown switch model {model}')


def get_monitored_ports(snmp, model):
    """ Get ports which meet the following conditions:
        - are configured to be no shutdown
        - and don't belong to a LAGG
        - or are a configured LAGG

        SNMP works in misterious ways: it is faster to fetch a whole table
        and then operate in this program than to fetch just a few entries.
    """

    ret = {}

    port_names = get_snmp_table(snmp, OIDS['port_name'])
    laggs = get_laggs(snmp, model)

    # Get only those ports which are up.
    port_states = {
        x: y for x, y
        in get_snmp_table(snmp, OIDS['port_state']).items()
        if y == 1
    }
    for port_idx, port_state in port_states.items():
        if not laggs or port_idx not in laggs.keys():
            port_name = standardize_portname(port_names[port_idx], model)
            if port_name:
                ret[port_idx] = port_name

    return ret


def get_laggs(snmp, model):
    """ Get only those LAGGs which have members """

    if model in ['powerconnect', 'procurve']:
        return {
            x: y for x, y
            in get_snmp_table(snmp, LAGG_OIDS[model]).items()
            if y != 0
        }

    return None


def standardize_portname(port_name, model):
    """ Return a Graphite-compatible port name or None if name
        can't be translated
    """
    r = PORT_REGEXP[model].match(port_name)
    if not r:
        return None
    g = r.group('port')
    if not g:
        return None
    return g.replace('/', '_').replace(':', '_')


def ports_stats(prefix, snmp, ports, model):
    """ Print graphite-compatible stats for each port of switch """

    for counter, oid in COUNTERS.items():
        # SNMP is slow that we want to get current time for each counter.
        template = prefix + '.ports.{}.{} {} ' + str(int(time()))
        table = get_snmp_table(snmp, oid)
        table_ignore = []
        if model in COUNTERS_IGNORE and counter in COUNTERS_IGNORE[model]:
            table_ignore = get_snmp_table(
                snmp, COUNTERS_IGNORE[model][counter]
            )
        for port_idx, port_name in ports.items():
            if port_idx in table:
                data = table[port_idx]
                if port_idx in table_ignore:
                    data -= table_ignore[port_idx]
                print(template.format(port_name, counter, data))


def dom_stats(prefix, snmp, ports, oids):
    """
    Print graphite-compatible Digital Optical Monitoring stats for each port
    of the switch
    """

    for metric, oid in oids.items():
        # SNMP is slow, so we want to get current time for each counter.
        timestamp = int(time())
        table = get_snmp_table(snmp, oid)
        for port_idx, port_name in ports.items():
            if port_idx not in table:
                continue
            data = table[port_idx]
            if not data:
                continue
            print(f'{prefix}.ports.{port_name}.{metric} {data} {timestamp}')


def cpu_stats(prefix, snmp, model):
    """ Print graphite-compatible stats of switch CPU

        We use single OID which should percentage of CPU time used.
    """

    cpu_usage = get_snmp_value(snmp, CPU_OIDS[model])

    if model == 'cumulus':
        # The value is percent idle
        cpu_usage = 100 - cpu_usage

    if model == 'powerconnect':
        # SNMP returns such ugly string
        #     5 Secs ( 18.74%)    60 Secs ( 17.84%)   300 Secs ( 18.12%)
        m = re.search('60 Secs \( *([0-9]+)[0-9\.]*%\)', cpu_usage)
        cpu_usage = int(m.group(1))
    if model == 'edgeswitch':
        # SNMP returns such ugly string
        #    5 Sec (  0.00%)    60 Sec (  0.12%)   300 Sec (  0.13%)
        m = re.search('60 Sec \( *([0-9]+)\.[0-9]+%\)', cpu_usage)
        cpu_usage = int(m.group(1))
    elif model == 'cumulus':
        # The value is percent idle
        cpu_usage = 100 - cpu_usage
    else:
        cpu_usage = int(cpu_usage)

    template = prefix + '.cpu {} ' + str(int(time()))
    print(template.format(cpu_usage))


if __name__ == '__main__':
    sys.exit(main())
