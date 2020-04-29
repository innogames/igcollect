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
    """
    parse args

    gets information from the outside of this program

    :return:
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Script to collect statuscodes from nginx')
    parser.add_argument('--logfile', default='/var/log/nginx/access.log',
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
    """

    main

    controls whats done throughout the program

    :return:
    """

    args = parse_args()
    prob_time = int(time.time())
    search_time = datetime.datetime.utcnow()

    with open(args.logfile) as log:

        log_for_period = get_log_for_period(log, search_time, 60, args.time)

        codes, total = count_uniq_statuscodes(log_for_period, args.position)

        template = args.prefix + '{}.{} {} {}'

        for code in codes.keys():
            print(template.format(
                '.status_codes', code, codes[code], prob_time))

        print(template.format('', 'requests', total, prob_time))


def get_log_for_period(log, timedate_at_start, period_in_sec, time_position):
    """
    get log gor period

    this algorithm is designed to search for the given timespan with as low of
    performance impact as possible so it searches for the beginning and the
    end of the period its looking for.

    :param log: the logfile
    :param timedate_at_start: what time the script started
    :param period_in_sec: how long the period to search is in seconds
    :param time_position: which position the time has in the log file
    :return: the log for the period found
    """

    start = 0
    stop = 0

    # search for first entry of period to check:
    for i in range(period_in_sec):
        start = find_row(
            log, timedate_at_start, -period_in_sec + i, time_position)
        if start != -1:
            break

    # search for the last entry in the period (if exists):
    stop = find_row(log, timedate_at_start, 1, time_position, start) - 1
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
    """
    count uniq statuscodes

    looks up witch and how often witch statuscode was found

    :param log: the logfile
    :param position: the position of the statuscode in the log
    :return: a dict of statuscodes and how often they got found, and the total
             amount of statuscodes
    """

    statuscodes = []
    for entry in log:
        statuscodes.append(entry[position])
    statuscodes_counted = Counter(statuscodes)

    return statuscodes_counted, len(statuscodes)


def get_position(position, entry):
    """
    get position

    returns a position out of a string

    :param position: the position in the string
    :param entry: the string
    :return:
    """

    return entry.split(' ')[position]


def add_seconds_to_time(time, seconds):
    """
    add seconds to time

    adds the given amount of seconds to the time

    :param time: the time that gets calculated
    :param seconds: the amount of seconds that get added
           (negative amounts possible)
    :return: the calculated time
    """

    new_time = time + datetime.timedelta(seconds=seconds)
    return new_time.strftime('%d/%b/%Y:%H:%M:%S')


def find_row(log, timedate_at_start, seconds_to_add, time_position, start=0):
    """
    find row

    searches for the the row of the log with a specific time stamp

    :param log: the logfile
    :param timedate_at_start: the time at wich the script was started
    :param seconds_to_add: how many seconds should get addet if nothing is
           found (accepts negative values)
    :param time_position: witch position hast the time in an entry
    :param start: in which line the search should start
    :return: number of entry or -1 if nothing is found
    """

    log.seek(start)
    for number_of_entry, entry in enumerate(log, start):
        search_time = add_seconds_to_time(timedate_at_start, seconds_to_add)
        if search_time in get_position(time_position, entry):
            return number_of_entry
    return -1


if __name__ == '__main__':
    main()
