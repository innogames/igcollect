#!/usr/bin/env python
"""igcollect - Linux cgroup v2 resource usage

Copyright (c) 2026 InnoGames GmbH
"""

from argparse import ArgumentParser
from os import listdir, path
from re import compile as re_compile, sub
from time import time

# Files with a single integer value ('max' = unlimited is skipped)
SINGLE_VALUE_FILES = (
    'memory.current',
    'memory.high',
    'memory.max',
    'memory.swap.current',
    'memory.swap.max',
    'pids.current',
)

# Files with "key value" lines: (file, metric prefix, keys to keep or None)
KEYED_FILES = (
    ('memory.stat', 'memory', (
        'anon',
        'file',
        'shmem',
        'pgmajfault',
        'workingset_refault_anon',
        'workingset_refault_file',
        'pswpin',               # newer kernels only
        'pswpout',              # newer kernels only
        'zswpin',
        'zswpout',
    )),
    ('memory.events', 'memory.events', None),
    ('memory.swap.events', 'memory.swap.events', None),
    ('cpu.stat', 'cpu', (
        'usage_usec',
        'user_usec',
        'system_usec',
        'nr_periods',
        'nr_throttled',
        'throttled_usec',
    )),
)

IO_STAT_KEYS = ('rbytes', 'wbytes', 'rios', 'wios')
PRESSURE_RESOURCES = ('cpu', 'memory', 'io')


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='cgroup')
    parser.add_argument('--root', default='/sys/fs/cgroup')
    parser.add_argument(
        '--depth', type=int, default=2,
        help='How deep to descend, 2 = system.slice/alloy.service',
    )
    parser.add_argument(
        '--exclude', default=r'\.(scope|mount|socket|swap)$',
        help='Regex of cgroup names to skip',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Only cgroup v2 (unified hierarchy) is supported
    if not path.isfile(path.join(args.root, 'cgroup.controllers')):
        return

    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    exclude = re_compile(args.exclude)

    for cgroup in find_cgroups(args.root, args.depth, exclude):
        name = metric_name(path.relpath(cgroup, args.root))
        for key, value in sorted(get_cgroup_stats(cgroup).items()):
            print(template.format(name, key, value))


def find_cgroups(directory, depth, exclude):
    """Yield cgroup directories up to the given depth"""
    if depth <= 0:
        return
    for entry in sorted(listdir(directory)):
        full_path = path.join(directory, entry)
        if not path.isdir(full_path) or exclude.search(entry):
            continue
        yield full_path
        for child in find_cgroups(full_path, depth - 1, exclude):
            yield child


def metric_name(relative_path):
    """system.slice/getty@tty1.service -> system_slice.getty_tty1_service"""
    return '.'.join(
        sub(r'[^A-Za-z0-9_-]', '_', part) for part in relative_path.split('/')
    )


def get_cgroup_stats(cgroup):
    ret = {}

    for file_name in SINGLE_VALUE_FILES:
        value = read_single(path.join(cgroup, file_name))
        if value is not None:
            ret[file_name] = value

    for file_name, prefix, keys in KEYED_FILES:
        for key, value in read_keyed(path.join(cgroup, file_name)).items():
            if keys is None or key in keys:
                ret['{}.{}'.format(prefix, key)] = value

    ret.update(read_io_stat(path.join(cgroup, 'io.stat')))

    for resource in PRESSURE_RESOURCES:
        ret.update(read_pressure(
            path.join(cgroup, resource + '.pressure'), resource
        ))

    return ret


def read_lines(file_path):
    # Missing files are normal: controllers may not be enabled everywhere
    try:
        with open(file_path, 'r') as fp:
            return fp.read().splitlines()
    except (IOError, OSError):
        return []


def read_single(file_path):
    lines = read_lines(file_path)
    if not lines or lines[0].strip() == 'max':
        return None
    return int(lines[0])


def read_keyed(file_path):
    ret = {}
    for line in read_lines(file_path):
        key, value = line.split()
        ret[key] = int(value)
    return ret


def read_io_stat(file_path):
    """Parse '8:0 rbytes=.. wbytes=.. rios=.. wios=..' per device"""
    ret = {}
    for line in read_lines(file_path):
        fields = line.split()
        # Resolve major:minor to a device name, e.g. 253:0 -> dm-0
        device = path.basename(path.realpath('/sys/dev/block/' + fields[0]))
        for field in fields[1:]:
            key, value = field.split('=')
            if key in IO_STAT_KEYS:
                ret['io.{}.{}'.format(device, key)] = int(value)
    return ret


def read_pressure(file_path, resource):
    """Parse PSI: 'some avg10=0.00 avg60=0.00 avg300=0.00 total=123'"""
    ret = {}
    for line in read_lines(file_path):
        kind, fields = line.split(None, 1)
        for field in fields.split():
            key, value = field.split('=')
            if key in ('avg10', 'total'):
                ret['pressure.{}.{}.{}'.format(resource, kind, key)] = value
    return ret


if __name__ == '__main__':
    main()