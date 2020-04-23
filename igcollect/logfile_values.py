#!/usr/bin/env python
"""igcollect - Values from Log File

This script can retrieve last line values by column number:

python logfile_values.py --metric "metric1:1" "metric2:2" ...

And aggregate data by time period with different functions:

median, mean, sum, min, max, count, frequency, speed (??)

count_100 - counts values > 100
count_100_percentage - estimates percentage of values > 100

python logfile_values.py --metric "metric1:1:mean:1d" \
                         --metric "metric2:3:count:60s"

Copyright (c) 2019 InnoGames GmbH
"""

import re
import os
import gzip
import logging
import datetime

from os.path import exists
from argparse import ArgumentParser, ArgumentTypeError


class Metric:
    def __init__(self, arg):
        if ':' not in arg:
            raise ArgumentTypeError('Argument must have ":"')
        parts = arg.split(':')
        if len(parts) != 4 and len(parts) != 2:
            raise ValueError('Wrong number of options')

        # Accepts 2 or 4 options. If 2 then function and period are NULL
        parts += [None] * (4 - len(parts))
        self.name, column, function, period = parts
        if period:
            pattern = re.compile(r'^\d+[A-Za-z]{1,3}$')
            if not pattern.match(period):
                raise ArgumentTypeError('Period must have number and unit')

        self.column = column
        self.function = function
        self.period = period
        self.values = []  # Container for metric values
        self.last_value = 0
        self.now = int(datetime.datetime.now(datetime.timezone.utc)
                       .timestamp())

    def get_timeshift(self):
        if self.period:
            units = [
                ('s', 1),
                ('min', 60),
                ('h', 60 * 60),
                ('d', 60 * 60 * 24),
            ]
            for unit, mul in units:
                if self.period.lower().endswith(unit):
                    return int(self.period[:-len(unit)].strip()) * mul
        return 0

    def estimate_columns_value(self, fields):
        '''
        Apply some arithmetic on several columns if needed
        Warning: Estimates regardless of arithmetics rules
        '''
        arr = [
            s for s in self.column if s.isdigit() or s in ['/', '*', '+', '-']
        ]
        result = 0
        for index, value in enumerate(arr):
            try:
                if value.isdigit() and result == 0:
                    result += float(fields[int(value)])
                elif value == '/':
                    result = result / float(fields[int(arr[index + 1])])
                elif value == '*':
                    result = result * float(fields[int(arr[index + 1])])
                elif value == '+':
                    result = result + float(fields[int(arr[index + 1])])
                elif value == '-':
                    result = result - float(fields[int(arr[index + 1])])
            except ZeroDivisionError:
                result = 0
        return result

    def get_median(self):
        sorted_list = sorted(self.values)
        i = len(sorted_list)
        if not i % 2:
            return (sorted_list[(i // 2) - 1] + sorted_list[i // 2]) / 2
        return sorted_list[i // 2]

    def get_sum(self):
        return sum(self.values)

    def get_count(self, v=0):
        return sum(1 for x in self.values if x >= v)

    def get_count_percentage(self, v=0):
        return sum(1 for x in self.values if x >= v) / len(self.values) * 100

    def get_mean(self):
        return sum(self.values) / len(self.values)

    def get_min(self):
        return min(self.values)

    def get_max(self):
        return max(self.values)

    def get_last_value(self):
        return self.last_value

    def get_frequency(self, v=0):
        return self.get_count(v) / self.get_timeshift()

    def get_speed(self):
        # Speed :-/?
        return self.get_sum() / self.get_timeshift()

    def get_distribution(self):
        d = {}
        uniq_values = set(self.values)
        for v in uniq_values:
            d[int(v)] = self.values.count(v)
        return d

    def get_metric_value(self):
        if not self.values:
            return 0

        if not self.function:
            return float(self.get_last_value())

        if self.function == 'distribution':
            return getattr(self, 'get_' + self.function)()

        if self.function.startswith('count_'):
            if self.function.endswith('percentage'):
                return float(
                    self.get_count_percentage(
                        int(self.function.split('_')[1])))
            return float(
                self.get_count(int(self.function.split('_')[1])))

        return float(getattr(self, 'get_' + self.function)())


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='logfile_values')
    parser.add_argument('--file', default='/var/log/messages')
    parser.add_argument('--columns-num', default='0', type=int)
    parser.add_argument('--metric', type=Metric, nargs='+')
    parser.add_argument('--time-column', default='0', type=int)
    parser.add_argument(
        '--time-format', default='%Y-%m-%dT%H:%M:%S%z',
        help='If timezone is not specified, time string is treated as '
        'local time',
    )
    parser.add_argument('--arch', action='store_true')
    parser.add_argument('--debug', '-d', action='store_true')
    return parser.parse_args()


def get_metrics_values(line, metrics, time_format, columns_num, time_column):
    fields = line.split()
    if columns_num and len(fields) != columns_num:
        return True

    timestamp = convert_to_timestamp(fields[time_column], time_format)
    for metric in metrics:
        if timestamp > metric.now - metric.get_timeshift():
            value = metric.estimate_columns_value(fields)
            metric.values.append(value)
        else:
            return False
    return True


def get_metrics_last_value(line, metrics):
    fields = line.split()
    for metric in metrics:
        metric.last_value = metric.estimate_columns_value(fields)


def read_logfile_reverse(filename,
                         columns_num,
                         time_column,
                         time_format,
                         metrics,
                         buf_size=8192):
    """
    A generator that returns the lines of a file in reverse order.
    Stops to read when has met timestamp bigger then desired period.

    Returns False if file was not read completely.
    """

    # If the log file does not exist (yet) just exit but do not report values
    # with a value of 0 or fail with an exception.
    if not exists(filename):
        exit(0)

    with open(filename) as fh:
        global_index = 0
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.splitlines()
            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concact the segment to the last line of new chunk
                # instead, yield the segment first
                if buffer[-1] != '\n':
                    lines[-1] += segment
                else:
                    yield get_metrics_values(
                        segment, metrics, time_format,
                        columns_num, time_column
                    )
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                global_index += 1
                if lines[index]:
                    if global_index == 1:
                        get_metrics_last_value(lines[index], metrics)
                    yield get_metrics_values(lines[index], metrics,
                                             time_format, columns_num,
                                             time_column)

    if segment is not None:
        yield get_metrics_values(segment, metrics, time_format,
                                 columns_num, time_column)


def convert_to_timestamp(time_str, time_format):
    """
    Disclamer about timezone part:
        if time_format doesn't specify timezone position, time tuple is treated
        as local
    """
    try:
        # Python cannot parse ISO8601 dates with suffix Z for UTC which is a
        # valid representation so we need to help it in advance.
        if time_format.endswith('z') and time_str.endswith('Z'):
            time_str = time_str[:-1] + '+0000'

        # We have seen some wrong formats returning ISO8601 dates with suffix Z
        # with a colon separated e.g. +01:00 this needs to be fixed.
        if time_format.endswith('z') and time_str[-3] == ':':
            time_str = ''.join(time_str.rsplit(':', 1))

        timestamp = datetime.datetime.strptime(time_str,
                                               time_format).timestamp()
    except ValueError:
        timestamp = int(time_str)
    return int(timestamp)


def main():  # NOQA: C901
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(logging.StreamHandler())

    file_was_readed = True

    # Read from the end of file until the timestamp is satisfying conditions
    data = read_logfile_reverse(
        args.file, args.columns_num, args.time_column,
        args.time_format, metrics=args.metric
    )
    for log_value in data:
        # Stop reading if next line has bigger timestamp as a required
        if not log_value:
            file_was_readed = log_value
            break

    # If the main file was read completely and there is arch flag then
    # check archive files for the presence of a timestamp satisfying condition
    if args.arch and file_was_readed:
        archive_pattern = re.compile(r'{}\.1\.gz'.format(
            os.path.basename(args.file)))  # parse only first (newest) archive
        for root, dirs, files in os.walk(os.path.dirname(args.file)):
            for f in files:
                if archive_pattern.search(f):
                    archive_file = os.path.join(root, f)
                    logging.getLogger().debug(
                        'Parsing archive file: {}'.format(f))
                    with gzip.open(archive_file, 'rt', encoding='utf-8') as fh:
                        for line in fh:
                            get_metrics_values(
                                line,
                                args.metric,
                                args.time_format,
                                args.columns_num,
                                args.time_column,
                            )

    for metric in args.metric:
        template = args.prefix + '.{} {} ' + str(metric.now)
        value = metric.get_metric_value()
        if isinstance(value, dict):
            for k, v in value.items():
                print(template.format(metric.name + '.' + str(k), v))
        else:
            print(template.format(metric.name, metric.get_metric_value()))


if __name__ == '__main__':
    main()
