#!/usr/bin/env python3
"""igcollect - Linux Disk I/O latency

Copyright (c) 2019 InnoGames GmbH
"""

from argparse import ArgumentParser
from subprocess import check_output
from time import time
import sys
from libvirt import (
    open as libvirt_open,
    libvirtError,
)


def parse_args():
    parser = ArgumentParser()

    parser.add_argument(
        '--prefix', dest='prefix', type=str, default='None',
        help='Graphite Metric Prefix')

    parser.add_argument(
        '--storagepool', dest='storagepool', type=str, required=True,
        help='Libvirt Storage Pool Name')

    parser.add_argument(
        '--storagevol', dest='storagevol', type=str, required=True,
        help='Libvirt Storage Volume Name')

    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))

    try:
        conn = libvirt_open('qemu:///system')
    except libvirtError as e:
        print(
            'An Exception has occured while openning a connection to '
            'qemu:///system: {}'.format(e)
        )
        exit(1)

    try:
        storage_pool = conn.storagePoolLookupByName(args.storagepool)
    except libvirtError as e:
        print(
            'An Exception has occured while finding {} pool: {}'
            .format(args.storagepool, e)
        )
        exit(1)

    try:
        storage_volume = storage_pool.storageVolLookupByName(args.storagevol)
    except libvirtError as e:
        print(
            'An exception has occured while opening the volume: {} {}'
            .format(args.storagevol, e)
        )
        exit(1)

    storage_volume_path = storage_volume.path()

    output_read = check_output(
        [
            '/usr/bin/sudo',
            '/usr/bin/ioping',
            '-BD',
            '-c10',
            '-i0.1',
            storage_volume_path
        ],
        universal_newlines=True
    )

    output_write = check_output(
        [
            '/usr/bin/sudo',
            '/usr/bin/ioping',
            '-BDWWW',
            '-c10',
            '-i0.1',
            storage_volume_path
        ],
        universal_newlines=True
    )

    output = {
        'read': output_read,
        'write': output_write,
    }

    for mode, data in output.items():
        measurement = data.split()

        results = {
            'min': measurement[4],
            'avg': measurement[5],
            'max': measurement[6],
        }

        for k, v in results.items():
            print(template.format(mode, k, int(v)))


if __name__ == '__main__':
    main()
