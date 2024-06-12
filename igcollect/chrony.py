#!/usr/bin/env python3
"""igcollect - Chrony NTP metrics collection

Copyright (c) 2024 InnoGames GmbH
"""

import csv
import platform
import time
from argparse import ArgumentParser
from subprocess import check_output


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='chrony')
    return parser.parse_args()


def main():
    args = parse_args()
    now = str(int(time.time()))

    metrics = {
        'activity': parse_activity(),
        'tracking': parse_tracking(),
    }

    for category, data in metrics.items():
        for metric, value in data.items():
            print(f'{args.prefix}.{category}.{metric} {value} {now}')


def run_chronyc_command(command):
    if platform.system() == 'FreeBSD':
        chrony = '/usr/local/bin/chronyc'
    else:
        chrony = '/usr/bin/chronyc'

    chrony_info_raw = check_output(
        [chrony, '-c', command],
        universal_newlines=True,
        close_fds=False,
    ).splitlines()

    csv_data = csv.reader(chrony_info_raw, delimiter=',')

    return csv_data


def parse_activity():
    output = run_chronyc_command('activity')

    line = next(output)

    ret = {
        'online': line[0],
        'offline': line[1],
        'burst_online': line[2],
        'burst_offline': line[3],
        'unknown': line[4],
    }

    return ret


def parse_tracking():
    output = run_chronyc_command('tracking')

    line = next(output)

    ret = {
        'stratum': line[2],
        'ref_time': line[3],  # Timestamp, 9 digits precision
        'system_time_offset': line[4],  # Offset in seconds. Negative is too fast, positive is too slow
        'last_offset': line[5],  # Seconds
        'rms_offset': line[6],  # Seconds
        'frequency': line[7],  # ppm. Negative is too slow, positive is too fast
        'residual_freq': line[8],  # ppm
        'skew': line[9],  # ppm
        'root_delay': line[10],  # Seconds
        'root_dispersion': line[11],  # Seconds
        'update_interval': line[12],  # Seconds
    }

    return ret


if __name__ == '__main__':
    main()
