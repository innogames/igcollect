#!/usr/bin/env python3
"""igcollect - Linux Disk I/O latency

Copyright (c) 2019 InnoGames GmbH
"""

from argparse import ArgumentParser
from subprocess import check_output
from time import time


def parse_args():
    parser = ArgumentParser()

    parser.add_argument(
        '--prefix', default='None',
        help='Graphite Metric Prefix')

    parser.add_argument(
        '--path', help='Path to check, by default libvirt is used.')

    parser.add_argument(
        '--size', default='4k',
        help='Request size in byte')

    parser.add_argument(
        '--storagepool', help='Libvirt Storage Pool Name')

    parser.add_argument(
        '--storagevol', help='Libvirt Storage Volume Name')

    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    path = get_path(args)

    ioping_args = [
        '/usr/bin/sudo',
        '/usr/bin/ioping',
        '-c10',   # make 10 requests
        '-i0.1',  # interval in sec
        '-B',     # print final statistics in raw format
        '-D'      # direct I/O
    ]

    if args.size is not None:
        ioping_args.append(f'-s{args.size}')

    output_read = check_output(
        ioping_args + [path],
        universal_newlines=True
    )

    output_write = check_output(
        ioping_args + ['-WWW', path],
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


def get_path(args) -> str:
    if args.path is not None:
        return args.path

    # no --path is specified -> use libvirt to get the storage volume
    from libvirt import (
        open as libvirt_open,
        libvirtError,
    )

    if args.storagepool is None or args.storagevol is None:
        raise Exception(
            'if --path is not set, --storagepool AND --storagevol are required'
        )

    try:
        conn = libvirt_open('qemu:///system')
    except libvirtError as e:
        raise Exception(
            'An Exception has occurred while opening a connection to '
            'qemu:///system: {}'.format(e)
        ) from e
    try:
        storage_pool = conn.storagePoolLookupByName(args.storagepool)
    except libvirtError as e:
        raise Exception(
            'An Exception has occurred while finding {} pool: {}'.format(
                args.storagepool, e
            )
        ) from e
    try:
        storage_volume = storage_pool.storageVolLookupByName(args.storagevol)
    except libvirtError as e:
        raise Exception(
            'An exception has occurred while opening the volume: {} {}'.format(
                args.storagevol, e
            )
        ) from e
    storage_volume_path = storage_volume.path()

    return storage_volume_path


if __name__ == '__main__':
    main()
