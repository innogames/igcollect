#!/usr/bin/env python
#
# igcollect - Switch port traffic over SNMP
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
from argparse import ArgumentParser

import re
import subprocess
import time

port_name_oid = '.1.3.6.1.2.1.31.1.1.1.1'
procurve_trunk_oid = '.1.3.6.1.4.1.11.2.14.11.5.1.7.1.3.1.1.8'
cisco_agg_oid = '.1.2.840.10006.300.43.1.2.1.1.12'

COUNTERS = {
    'bytesIn': '.1.3.6.1.2.1.31.1.1.1.6',
    'bytesOut': '.1.3.6.1.2.1.31.1.1.1.10',
    'pktsIn': '.1.3.6.1.2.1.31.1.1.1.7',
    'pktsOut': '.1.3.6.1.2.1.31.1.1.1.11',
    'brdPktsIn': '.1.3.6.1.2.1.31.1.1.1.9',
    'brdPktsOut': '.1.3.6.1.2.1.31.1.1.1.13',
    'ifInErrors': '.1.3.6.1.2.1.2.2.1.14',
    'ifOutErrors': '.1.3.6.1.2.1.2.2.1.20',
    'ifInDiscards': '.1.3.6.1.2.1.2.2.1.13',
    'ifOutDiscards': '.1.3.6.1.2.1.2.2.1.19',
}


def get_snmp_value(host, community, node_name):
    """ Function retriving value of given command.
        In the current version only one row response is handled:
        return last value retireved via SNMP
    """

    proc = subprocess.Popen(
        ['snmpwalk', '-On', '-c', community, '-v2c', host, node_name],
        stdout=subprocess.PIPE,
    )

    resp = proc.stdout.read()
    rex = re.compile(r'^([0-9\.]+) = ((.*): )?"?([^"]*)')
    rem = rex.match(resp)

    if rem:
        return rem.groups()[3]
    return None


def get_snmp_table(host, community, table_oid, skip):
    ''' Retrieves whole table of SNMP values at once.
        This should be faster than snmpwalk/get on each OID separately.
        If a non-null skip is given, last number in OID is compared
        to the parameter and skipped if bigger.
    '''

    snmp_proc = subprocess.Popen(
        ['snmpwalk', '-On', '-c', community, '-v2c', host, table_oid],
        stdout=subprocess.PIPE,
    )

    rex = re.compile(r'^([0-9\.]+) = ((.*): )?"?([^"]*)')
    ret_dict = {}
    ret_lines = snmp_proc.stdout.readlines()

    if 'No Such Object available on this agent at this OID' in ret_lines[0]:
        # Would be so much easier to just get snmpwalk return code but
        # unfortunately it always terminates with code 0
        return None

    for line in ret_lines:
        line = line.rstrip()
        # example row:
        # .1.3.6.1.2.1.31.1.1.1.6.48 = Counter64: 2861909107355
        rem = rex.match(line)
        if rem:
            reg = rem.groups()
            res_oid = reg[0]
            res_value = reg[3]
            res_array = res_oid.split('.')
            res_num = int(res_array[-1])
            if skip:
                if res_num < skip:
                    ret_dict[res_num] = res_value
            else:
                ret_dict[res_num] = res_value

    return ret_dict


def get_switch_data(switch, community):
    switch_model = get_snmp_value(switch, community, '.1.3.6.1.2.1.1.1.0')

    if switch_model is None:
        return

    skip = None

    if 'PowerConnect' in switch_model:
        port_name_dict = get_snmp_table(switch, community, port_name_oid, None)
        switch_type = 'Dell'
        trunk_group_tab = get_snmp_table(switch, community, cisco_agg_oid, 0)
        trunked_ports = set()
        active_lags = set()
        for port_idx in trunk_group_tab:
            if int(trunk_group_tab[port_idx]) > 0:
                trunked_ports.add(int(port_idx))
                active_lags.add(int(trunk_group_tab[port_idx]))

    elif 'ProCurve' in switch_model:
        port_name_dict = get_snmp_table(switch, community, port_name_oid, None)
        switch_type = 'ProCurve'
        trunk_group_tab = get_snmp_table(switch, community,
                                         procurve_trunk_oid, 0)

    elif 'ExtremeXOS' in switch_model:
        port_name_dict = get_snmp_table(switch, community,
                                        port_name_oid, 1000000)
        switch_type = 'Extreme'
        trunk_group_tab = None
        skip = 1000000

    port_num = 0
    snmp_tables = {}
    for counter, snmp_oid in COUNTERS.items():
        snmp_tables[counter] = get_snmp_table(
            switch, community, snmp_oid, skip
        )

    # Let's consider that "now" is after all values are
    # read for this particular switch.
    now = str(int(time.time()))

    for port_index, port_name in port_name_dict.items():
        # Skip bad ports. This can be a VLAN on Cisco device.
        if (
            port_index not in snmp_tables['bytesIn']
            or
            port_index not in snmp_tables['pktsIn']
        ):
            continue

        counters = {}
        for counter in COUNTERS:
            counters[counter] = int(snmp_tables[counter][port_index])

        # Is it a Trunk / etherchannel?
        if (
            (switch_type == 'Dell' and re.match('^Po[0-9]+$', port_name))
            or
            (switch_type == 'ProCurve' and re.match('^Trk[0-9]+$', port_name))
        ):
            # On Dell devices all portchannels are listed, so skip those unused
            if switch_type == 'Dell' and port_index not in active_lags:
                continue
        # Is it a real port?
        elif (
            (
                switch_type == 'Dell'
                and
                re.match('^(Gi|Te)[0-9]/[0-9]/[0-9]+$', port_name)
            )
            or
            (switch_type == 'ProCurve' and re.match('^[0-9]+$', port_name))
            or
            (switch_type == 'Extreme')
        ):
            # Get rid of unsupported characters from port name
            port_name = port_name.replace('/', '_').replace(':', '_')
            if switch_type == 'ProCurve':
                port_num = int(port_name)
            elif switch_type == 'Dell':
                # On Dell blade switches ports have non-contignous numbers,
                # there is space for extra 4 ports after each 20.
                port_num += 1
        else:
            continue

        # This means that this is a supported type of port and we want to
        # send its counters to Graphite
        for counter in COUNTERS:
            print("switches.{}.{}-{}.{} {} {}".format(
                switch, port_index, port_name,
                counter, counters[counter], now
            ))


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '-c', '--community', type=str, required=True,
        help='SNMP community'
    )
    parser.add_argument(
        'switches', type=str, nargs='+',
        help='Hostname of a switch'
    )
    return parser.parse_args()


def main(args):
    for switch in args.switches:
        get_switch_data(switch, args.community)


if __name__ == '__main__':
    main(parse_args())
