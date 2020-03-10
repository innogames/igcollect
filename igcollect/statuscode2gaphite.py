import argparse
import datetime
import time
import socket

from collections import Counter


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Script to collect statuscodes from nginx')
    parser.add_argument('logfile',
                        help='path to logfile')
    parser.add_argument('-s', '--software', default='nginx',
                        help='which tool is using it ')
    parser.add_argument('-t', '--time', type=int, default=3,
                        help='where to search for the time in the log file ')
    parser.add_argument('-x', '--position', type=int, default=8,
                        help='where to search for the code in the log file ')
    parser.add_argument('-p', '--prefix',
                        default='servers.{}.software.{}'.format(
                            socket.gethostname().replace('.', '_'),
                            parser.parse_args().software),
                        help='the path to the value in Graphite ')
    return parser.parse_args()


def get_position(position, entry):
    return entry[position]


def get_lines(path):
    log_file = open(path)
    log = []
    for line in log_file:
        log.append(line.split(' '))
    return log


def count_uniq_statuscodes(log, position):
    statuscodes = []
    for entry in log:
        statuscodes.append(entry[position])
    statuscodes_sorted = dict(Counter(statuscodes))

    return statuscodes_sorted, len(statuscodes)


def add_seconds_to_time(time, seconds):
    new_time = time + datetime.timedelta(seconds=seconds)
    return new_time.strftime('%d/%b/%Y:%H:%M:%S')


def find_row(log, timedate_at_start, seconds_to_add, time_position):
    for number_of_entry, entry in enumerate(log):
        search_time = add_seconds_to_time(timedate_at_start, seconds_to_add)
        if search_time in get_position(time_position, entry):
            return number_of_entry
    return -1


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
        if start != -1:
            stop -= 1
            break

    # return everything in this period:
    return log[start:stop]


def main():
    args = parse_args()
    prob_time = int(time.time())
    search_time = datetime.datetime.utcnow()

    log = get_lines(args.logfile)

    log_for_period = get_log_for_period(log, search_time, 60, args.time)

    codes, total = count_uniq_statuscodes(log_for_period, args.position)

    print(log_for_period)

    template = args.prefix + '{}.{} {} {}'

    for key in codes.keys():
        print(template.format('.status_codes', key, codes[key], prob_time))

    print(template.format('', 'requests', total, prob_time))


if __name__ == '__main__':
    main()
