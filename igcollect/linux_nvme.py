#!/usr/bin/env python3
"""igcollect - Linux NVMe SMART

Copyright (c) 2026 InnoGames GmbH
"""

import json
import sys
from argparse import ArgumentParser, Namespace
from os import listdir
from subprocess import CalledProcessError, PIPE, check_output
from time import time


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='nvme')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = int(time())

    for disk_name, device in get_nvme_devices().items():
        stats = get_smart_log(device)
        for key, raw_value in stats.items():
            print(f'{args.prefix}.{disk_name}.{key} {parse_value(key, raw_value)} {timestamp}')


def get_nvme_devices() -> dict:
    """Discover NVMe devices via sysfs.

    Returns a dict mapping disk name (model-serial) to device node name.
    """
    sysfs_base = '/sys/class/nvme'
    devices = {}
    try:
        entries = listdir(sysfs_base)
    except FileNotFoundError:
        return devices

    for entry in entries:
        try:
            with open(f'{sysfs_base}/{entry}/model') as f:
                model = sanitize_component(f.read())
            with open(f'{sysfs_base}/{entry}/serial') as f:
                serial = sanitize_component(f.read())
        except OSError as e:
            print(f'ERROR: could not read sysfs attributes for {entry}: {e}', file=sys.stderr)
            continue
        devices[f'{model}-{serial}'] = entry

    return devices


def get_smart_log(device: str) -> dict:
    """Retrieve SMART log for an NVMe device as a dict."""
    try:
        output = check_output(
            ['nvme', 'smart-log', f'/dev/{device}', '--output-format=json'],
            stderr=PIPE,
        )
        return json.loads(output)
    except FileNotFoundError as e:
        print(f'ERROR: nvme-cli is not available while reading SMART log for {device}: {e}', file=sys.stderr)
    except CalledProcessError as e:
        stdout = e.stdout.decode(errors='replace').strip()
        stderr = e.stderr.decode(errors='replace').strip()
        print(f'ERROR: could not read SMART log for {device}: {e}\nstdout: {stdout}\nstderr: {stderr}', file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f'ERROR: could not parse SMART log JSON for {device}: {e}', file=sys.stderr)
    return {}


def parse_value(key: str, raw) -> int:
    """Convert a smart-log value to an integer.

    Comma-formatted strings (e.g. "13,636,313,406") are stripped before
    conversion. Temperature fields are converted from Kelvin to Celsius.
    """
    value = int(str(raw).replace(',', ''))
    if key.startswith('temperature'):
        value -= 273
    return value

def sanitize_component(value: str):
    """Replace graphite incompatible values from the metric path."""
    return value.strip().replace(' ', '_').replace('.', '_')


if __name__ == '__main__':
    main()
