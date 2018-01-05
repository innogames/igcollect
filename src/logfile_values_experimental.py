#!/usr/bin/env python
#
# logfile_values.py
#
# Copyright (c) 2017, InnoGames GmbH
#
"""
logfile_values.py -- a python script to find metrics values in log file

This script is using last line of log file to get metric value by column number

python logfile_values.py --metric "metric1:1" "metric2:2" ...
"""
import re
import time
import os
import gzip
import logging

from argparse import ArgumentParser, ArgumentTypeError
from datetime import timedelta


class Metric:
    def __init__(self, arg):
        if ':' not in arg:
            raise ArgumentTypeError('Argument must have ":"')
        parts = arg.split(':')
        if len(parts) != 4 and len(parts) != 2:
            raise ValueError('Wring number of options')

        # Accepts 2 or 4 options. If 2 then function and period are NULL
        parts += [None] * (4 - len(parts))
        self.name, column, function, period = parts
        if period:
            pattern = re.compile("^\d+[A-Za-z]$")
            if not pattern.match(period):
                raise ArgumentTypeError('Period must have number and unit')
        if not column.isdecimal():
            raise ArgumentTypeError('Column must be a number')
        self.column = int(column)
        self.function = function
        self.period = period
        # Here is container for metric values
        self.values = []
        self.last_value = 0

    def get_timeshift(self):
        if self.period:
            value = int(self.period[:-1])
            unit = self.period[-1].lower()
            now = int(time.time())
            if unit == 's':
                return timedelta(seconds=value).total_seconds()
            elif unit == 'm':
                return timedelta(minutes=value).total_seconds()
            elif unit == 'h':
                return timedelta(hours=value).total_seconds()
            elif unit == 'd':
                return timedelta(days=value).total_seconds()
        else:
            return 0

    def get_median(self):
        l = sorted(self.values)
        i = len(l)
        if not i % 2:
            return (l[(i // 2) - 1] + l[i // 2]) / 2
        return int(l[i // 2])

    def get_sum(self):
        return int(sum(self.values))

    def get_count(self, v=0):
        return int(sum(1 for x in self.values if x > v))

    def get_mean(self):
        return int(sum(self.values) / len(self.values))

    def get_min(self):
        return int(min(self.values))

    def get_max(self):
        return int(max(self.values))

    def get_last_value(self):
        return int(self.last_value)

    def get_metric_value(self):
        f = self.function
        if f == 'mean':
            return self.get_mean()
        elif f == 'median':
            return self.get_median()
        elif f == 'sum':
            return self.get_sum()
        elif f == 'min':
            return self.get_min()
        elif f == 'max':
            return self.get_max()
        elif f == 'count':
            return self.get_count()
        elif f == 'last' or not f:
            return self.get_last_value()
        else:
            raise ArgumentTypeError(
                'Wrong function. Possible functions: blablabla')


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='logfile_values')
    parser.add_argument('--file', default='/var/log/messages')
    parser.add_argument('--metric', type=Metric, nargs='+')
    parser.add_argument('--time_format', default='%Y-%m-%dT%H:%M:%S')
    parser.add_argument('--arch', action='store_true')
    parser.add_argument('--debug', '-d', action='store_true')
    return parser.parse_args()


#https://stackoverflow.com/questions/2301789
def reverse_readline(filename, buf_size=8192):
    """a generator that returns the lines of a file in reverse order"""
    with open(filename) as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split('\n')
            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concact the segment to the last line of new chunk
                # instead, yield the segment first
                if buffer[-1] is not '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if len(lines[index]):
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


def convert_to_timestamp(time_str, time_format):
    try:
        timestamp = int(
            time.mktime(time.strptime(time_str.split("+")[0], time_format)))
    except ValueError:
        try:
            timestamp = int(
                time_str) 
        except ValueError:
            timestamp = int(
                time.mktime(
                    time.strptime('-'.join(time_str.split("-")[:-1]),
                                  time_format)))
        pass
    return int(timestamp)


def main():
    args = parse_args()
    file = args.file

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.getLogger().addHandler(logging.StreamHandler())
    now = int(time.time())
    template = args.prefix + '.{} {} ' + str(now)
    for metric in args.metric:
        # Read from the end of file until the timestamp is satisfying conditions
        for line in reverse_readline(file):
            fields = line.split()
            fields[0] = convert_to_timestamp(fields[0], args.time_format)
            if fields[0] > (int(time.time()) - metric.get_timeshift()):
                metric.values.append(int(fields[metric.column]))
        # Check archive files for the presence of a timestamp satisfying condition
        if args.arch:
            dir_path = os.path.dirname(os.path.realpath(file))
            archive_pattern = re.compile(r'{}\.\d+?\.gz'.format(file))
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    print(f)
                    if archive_pattern.search(f):
                        archive_file = os.path.join(root, f)
                        logging.getLogger().debug(
                            'Parsing archive file: {}'.
                            format(f))
                        with gzip.open(f, 'rt', encoding='utf-8') as fh:
                            for line in fh:
                                fields = line.split()
                                fields[0] = convert_to_timestamp(
                                    fields[0], args.time_format)
                                if fields[0] > (int(time.time()) -
                                                metric.get_timeshift()):
                                    metric.values.append(
                                        int(fields[metric.column]))

    for metric in args.metric:
        print(template.format(metric.name, metric.get_metric_value()))


if __name__ == '__main__':
    main()
