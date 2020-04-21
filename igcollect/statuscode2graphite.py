#!/usr/bin/env python3

"""igcollect - statuscode2graphite
Copyright (c) 2020 InnoGames GmbH
"""

# This script is used to collect statuscodes out of the logs of nginx and
# similar services

import argparse
import datetime
import time

from collections import Counter


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Script to collect statuscodes from nginx')
    parser.add_argument('logfile',
                        help='path to logfile')
    parser.add_argument('-t', '--time', type=int, default=3,
                        help='where to search for the time in the log file ')
    parser.add_argument('-x', '--position', type=int, default=8,
                        help='where to search for the code in the log file ')
    parser.add_argument('-p', '--prefix',
                        default='nginx',
                        help='the path to the value in Graphite ')
    return parser.parse_args()


def main():
    args = parse_args()
    prob_time = int(time.time())
    search_time = datetime.datetime.utcnow()

    log = get_log(args.logfile)

    log_for_period = get_log_for_period(log, search_time, 60, args.time)

    codes, total = count_uniq_statuscodes(log_for_period, args.position)

    template = args.prefix + '{}.{} {} {}'

    for code in codes.keys():
        print(template.format('.status_codes', code, codes[code], prob_time))

    print(template.format('', 'requests', total, prob_time))


def get_log(path):
    log_file = open(path)
    return log_file


def get_log_for_period(log, timedate_at_start, period_in_sec, time_position):
    start = 0
    stop = 0

    # search for first entry of period to check:
    for i in range(period_in_sec):
        start = find_row(
            log, timedate_at_start, -period_in_sec + i, time_position)
        if start != -1:
            break

    # search for the last entry in the period (if exists):
    stop = find_row(log, timedate_at_start, 1, time_position) - 1
    for i in range(10):
        stop = find_row(log, timedate_at_start, 1, time_position)
        if stop != -1:
            stop -= 1
            break

    # return everything in this period:
    log_for_period = []
    if stop == -1:
        log.seek(0)
        for line, entry in enumerate(log):
            if line >= start:
                log_for_period.append(entry.split(' '))
    else:
        log.seek(0)
        for line, entry in enumerate(log):
            if line >= start and line <= stop:
                log_for_period.append(entry.split(' '))

    return log_for_period


def count_uniq_statuscodes(log, position):
    statuscodes = []
    for entry in log:
        statuscodes.append(entry[position])
    statuscodes_sorted = dict(Counter(statuscodes))

    return statuscodes_sorted, len(statuscodes)


def get_position(position, entry):
    return entry.split(' ')[position]


def add_seconds_to_time(time, seconds):
    new_time = time + datetime.timedelta(seconds=seconds)
    return new_time.strftime('%d/%b/%Y:%H:%M:%S')


def find_row(log, timedate_at_start, seconds_to_add, time_position):
    log.seek(0)
    for number_of_entry, entry in enumerate(log):
        search_time = add_seconds_to_time(timedate_at_start, seconds_to_add)
        if search_time in get_position(time_position, entry):
            return number_of_entry
    return -1


if __name__ == '__main__':
    main()
