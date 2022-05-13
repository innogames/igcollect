#!/usr/bin/env python3
"""igcollect - Switch

This script collects

* port traffic
* port errors
* CPU utilization

from a switch via SNMP.

Copyright (c) 2017 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time
from pysnmp import proto, error
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.entity.rfc3413.oneliner.cmdgen import (
        CommunityData,
        UsmUserData,
        usmHMACSHAAuthProtocol,
        usmAesCfb128Protocol,
        usmDESPrivProtocol,
)
import re
import sys

# Predefine some variables, it makes this program run a bit faster.
cmd_gen = cmdgen.CommandGenerator()

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
    'force10_mxl': re.compile('^(TenGigabitEthernet|fortyGigE) (?P<port>[0-9]+/[0-9]+)$'),
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


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('switch', type=str, help='Hostname of a switch')
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


def get_snmp_connection(args):
    """ Prepare SNMP transport agent.

        Connection over SNMP v2c and v3 is supported.
        The choice of authentication and privacy algorithms for v3 is
        arbitrary, matching what our switches can do.
    """

    if args.community:
        auth_data = CommunityData(args.community, mpModel=1)
    else:
        if args.priv_proto == 'des':
            priv_proto = usmDESPrivProtocol
        if args.priv_proto == 'aes':
            priv_proto = usmAesCfb128Protocol

        auth_data = UsmUserData(
            args.user, args.auth, args.priv,
            authProtocol=usmHMACSHAAuthProtocol,
            privProtocol=priv_proto,
        )

    transport_target = cmdgen.UdpTransportTarget((args.switch, 161))

    return {
        'auth_data': auth_data,
        'transport_target': transport_target,
    }


def get_snmp_value(snmp, OID):
    """ Get a single value from SNMP """

    errorIndication, errorStatus, errorIndex, varBinds = cmd_gen.getCmd(
        snmp['auth_data'],
        snmp['transport_target'],
        OID,
    )
    if errorIndication:
        raise SwitchException('Unable to get SNMP value: {}'.
                              format(errorIndication))

    return convert_snmp_type(varBinds)


def get_snmp_table(snmp, OID):
    """ Fetch a table from SNMP.

        Returned is a dictionary mapping the last number of OID (converted to
        Python integer) to value (converted to int or str).
    """
    ret = {}
    errorIndication, errorStatus, errorIndex, varBindTable = cmd_gen.bulkCmd(
        snmp['auth_data'],
        snmp['transport_target'],
        0,  # nonRepeaters
        25,
        OID,
    )
    for varBind in varBindTable:
        # Oh the joy of pysnmp library!
        # When the nonrepeaters value above is 0, we might get objects from
        # another snmp tree on some hardware, for example from cisco routers.
        # we can set it to 1 but then we have high cpu usage. So keep it 0
        # and manually check if we are still in the same tree.
        # OIDs we query for must not start with a dot.
        if not str(varBind[0][0]).startswith(OID):
            break
        if errorIndication:
            raise SwitchException('Unable to get SNMP value: {}'.
                                  format(errorIndication))
        index = int(str(varBind[0][0][-1:]))
        ret[index] = convert_snmp_type(varBind)

    return ret


def convert_snmp_type(varBinds):
    """ Convert SNMP data types to something more convenient: int or str """

    val = varBinds[0][1]
    if type(val) in [
        proto.rfc1902.Integer,
        proto.rfc1902.Counter32,
        proto.rfc1902.Counter64,
    ]:
        return int(val)
    return str(val)


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
        return'extreme'
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

    print('Unknown switch model {}'.format(model), file=sys.stderr)
    return None


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
        # SNMP is slow that we want need to get current time for each counter.
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
        print(cpu_usage)
        #m = re.search('(.*)', cpu_usage)
        #print(m.group(1))
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
