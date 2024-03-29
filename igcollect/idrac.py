#!/usr/bin/env python3
"""igcollect - idrac

This script collects various parameters of iDRAC and a server it is in via SNMP.

Copyright © 2023 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time

import sys

from lib_snmp import (
    add_snmp_arguments,
    get_snmp_connection,
    get_snmp_table,
)

OID_CONSTANTS = {
    'temperatureProbeTypeIsDiscrete': 16,
    'amperageProbeTypeIsDiscrete': 16,
    'amperageProbeTypeIsPowerSupplyAmps': 23,
    'amperageProbeTypeIsPowerSupplyWatts': 24,
    'amperageProbeTypeIsSystemAmps': 25,
    'amperageProbeTypeIsSystemWatts': 26,
}

OIDS = {
    'temperature': {
        # Defines the value of the temperature probe.
        # When the value
        # for temperatureProbeType is other than temperatureProbeTypeIsDiscrete,
        # the value returned for this attribute is the temperature that the
        # probe is reading in tenths of degrees Centigrade. When the value for
        # temperatureProbeType is temperatureProbeTypeIsDiscrete, a value is
        # not returned for this attribute.
        'probe_type': '1.3.6.1.4.1.674.10892.5.4.700.20.1.7',
        'probe_names': '1.3.6.1.4.1.674.10892.5.4.700.20.1.8',
        'probe_readings': '1.3.6.1.4.1.674.10892.5.4.700.20.1.6',
    },
    'current': {
        # 0600.0030.0001.0006 This attribute defines the reading for an amperage
        # probe of type other than amperageProbeTypeIsDiscrete.
        # When the value for amperageProbeType is amperageProbeTypeIsPowerSupplyAmps
        # or amperageProbeTypeIsSystemAmps, the value returned for this attribute
        # is the power usage that the probe is reading in tenths of Amps.
        # When the value for amperageProbeType is amperageProbeTypeIsPowerSupplyWatts
        # or amperageProbeTypeIsSystemWatts, the value returned for this attribute
        # is the power usage that the probe is reading in Watts.
        # When the value for amperageProbeType is other than amperageProbeTypeIsDiscrete,
        # amperageProbeTypeIsPowerSupplyAmps, amperageProbeTypeIsPowerSupplyWatts,
        # amperageProbeTypeIsSystemAmps or amperageProbeTypeIsSystemWatts,
        # the value returned for this attribute is the amperage that the probe is
        # reading in Milliamps.
        # When the value for amperageProbeType is amperageProbeTypeIsDiscrete,
        # a value is not returned for this attribute.
        'probe_type': '1.3.6.1.4.1.674.10892.5.4.600.30.1.7',
        'probe_unit_mapping': {
            OID_CONSTANTS['amperageProbeTypeIsDiscrete']: 'A',
            OID_CONSTANTS['amperageProbeTypeIsPowerSupplyAmps']: 'A',
            OID_CONSTANTS['amperageProbeTypeIsPowerSupplyWatts']: 'W',
            OID_CONSTANTS['amperageProbeTypeIsSystemAmps']: 'A',
            OID_CONSTANTS['amperageProbeTypeIsSystemWatts']: 'W',
            'default': 'mA',
        },
        'probe_names': '1.3.6.1.4.1.674.10892.5.4.600.30.1.8',
        'probe_readings': '1.3.6.1.4.1.674.10892.5.4.600.30.1.6',
    }
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('host', type=str, help='Hostname of the iDRAC')
    parser.add_argument('--prefix', help='Graphite prefix')
    add_snmp_arguments(parser)

    return parser.parse_args()


def main():
    timestamp = int(time())
    args = parse_args()

    snmp = get_snmp_connection(args)

    prefix = 'idrac'
    if args.prefix:
        prefix = f'{args.prefix}'

    for probe_set, probe_config in OIDS.items():
        if probe_set == 'temperature':
            probe_data = get_temperatures(snmp, probe_config)
        elif probe_set == 'current':
            probe_data = get_currents(snmp, probe_config)
        else:
            raise Exception(f'Unknown probe {probe_set}')

        for probe_name, probe_reading in probe_data.items():
            probe_name = probe_name.replace(' ', '_')
            print(f'{prefix}.{probe_set}.{probe_name} {probe_reading} {timestamp}')


def get_temperatures(snmp, config):
    ret = {}
    probe_units = get_snmp_table(snmp, config['probe_type'])
    for probe_index, probe_data in get_probes_table(snmp, config).items():
        if probe_units[probe_index] != OID_CONSTANTS['temperatureProbeTypeIsDiscrete']:
            ret[probe_data['name']] = probe_data['reading'] * 0.1
        # else skip this probe
    return ret


def get_currents(snmp, config):
    ret = {}
    probe_units = get_snmp_table(snmp, config['probe_type'])
    for probe_index, probe_data in get_probes_table(snmp, config).items():
        probe_unit = probe_units[probe_index]
        if probe_unit in config['probe_unit_mapping']:
            probe_unit = config['probe_unit_mapping'][probe_unit]
        else:
            probe_unit = config['probe_unit_mapping']['default']
        ret[f'{probe_data["name"]}.{probe_unit}'] = probe_data['reading']
    return ret


def get_probes_table(snmp, config):
    probe_names = get_snmp_table(snmp, config['probe_names'])
    probe_readings = get_snmp_table(snmp, config['probe_readings'])
    ret = {}
    for probe_index, probe_name in probe_names.items():
        ret[probe_index] = {
            'name': probe_name,
            'reading': probe_readings[probe_index],
        }
    return ret


if __name__ == '__main__':
    sys.exit(main())
