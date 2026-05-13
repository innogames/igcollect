#!/usr/bin/env python
"""igcollect - FreeBSD UMA Zone Memory Usage

Copyright © 2026 InnoGames GmbH
"""

import ctypes
import sysctl

from argparse import ArgumentParser
from time import time

# py-sysctl has a stale errno bug: Sysctl_getvalue() checks errno without
# clearing it first, so EISDIR from a directory node poisons subsequent
# leaf node reads.  Work around by clearing errno before each .value access.
_libc = ctypes.CDLL('libc.so.7')
_libc.__error.restype = ctypes.POINTER(ctypes.c_int)


def _clear_errno():
    _libc.__error()[0] = 0


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='uma')
    return parser.parse_args()


def sysctl_to_int(value):
    if type(value) == bytearray:
        return int.from_bytes(value, byteorder='little', signed=False)
    return value


def parse_uma_zones():
    zones = {}

    for line in sysctl.filter('vm.uma'):
        parts = line.name.split('.')
        # vm.uma.<zone>.<rest...>
        if len(parts) < 4:
            continue
        zone = parts[2]
        rest = '.'.join(parts[3:])
        if zone not in zones:
            zones[zone] = {}
        _clear_errno()
        zones[zone][rest] = sysctl_to_int(line.value)

    return zones


def main():
    args = parse_args()
    template = args.prefix + '.{} {} ' + str(int(time()))

    for zone, values in parse_uma_zones().items():
        count = values.get('stats.current')
        size = values.get('keg.rsize') or values.get('size')
        if count is not None and size is not None:
            print(template.format(zone, count * size))


if __name__ == '__main__':
    main()
