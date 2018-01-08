#!/usr/bin/env python
#
# logfile_values.py
#
# Copyright (c) 2017, InnoGames GmbH
#
"""
logfile_values.py -- a python script to find metrics values in log file

This script can retrive last line values by column number:

python logfile_values.py --metric "metric1:1" "metric2:2" ...

And aggregate data by time period with different functions:

median, mean, sum, min, max, count, frequency, speed (??)

count_100 - counts values > 100
count_100_percentage - estimates percentage of values > 100

python logfile_values.py  --metric "metric1:1:mean:1d" --metric "metric2:3:count:60s"

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
            raise ValueError('Wrong number of options')

        # Accepts 2 or 4 options. If 2 then function and period are NULL
        parts += [None] * (4 - len(parts))
        self.name, column, function, period = parts
        if period:
            pattern = re.compile("^\d+[A-Za-z]{1,3}$")
            if not pattern.match(period):
                raise ArgumentTypeError('Period must have number and unit')

        self.column = column
        self.function = function
        self.period = period
        # Here is container for metric values
        self.values = []
        self.last_value = 0
        self.start_timestamp = 0
        self.end_timestamp = 0
        self.now = int(time.time())

    def get_timeshift(self):
        if self.period:
            value = int(" ".join(re.findall("\d+", self.period.lower())))
            unit = " ".join(re.findall("[a-z]+", self.period.lower()))
            if unit == 's':
                return timedelta(seconds=value).total_seconds()
            if unit == 'min':
                return timedelta(minutes=value).total_seconds()
            if unit == 'h':
                return timedelta(hours=value).total_seconds()
            if unit == 'd':
                return timedelta(days=value).total_seconds()
        else:
            return 0

    def estimate_columns_value(self, fields):
        '''
        Apply some arithmetic on several columnsif needed
        Warning: Estimates regardless of arithmetics rules        
        '''
        arr = [
            s for s in self.column if s.isdigit() or s in ['/', '*', '+', '-']
        ]
        result = 0
        for index, value in enumerate(arr):
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
        return result

    def get_duration(self):
        '''Returns real duration when metric appeared in log file'''
        duration = self.end_timestamp - self.start_timestamp
        return duration

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
        return self.get_count(v) / self.get_duration()

    def get_speed(self):
        # Speed :-/?
        return self.get_sum() / self.get_duration()

    def get_metric_value(self):
        if self.function:
            if 'count_' in self.function:
                if 'percentage' in self.function:
                    return float(
                        self.get_count_percentage(
                            int(self.function.split('_')[1])))
                return float(self.get_count(int(self.function.split('_')[1])))
            return float(getattr(self, 'get_' + self.function)())
        return float(self.get_last_value())


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='logfile_values')
    parser.add_argument('--file', default='/var/log/messages')
    parser.add_argument('--columns-num', default='5', type=int)
    parser.add_argument('--metric', type=Metric, nargs='+')
    parser.add_argument('--time-format', default='%Y-%m-%dT%H:%M:%S')
    parser.add_argument('--arch', action='store_true')
    parser.add_argument('--debug', '-d', action='store_true')
    parser.add_argument('--time-zone', default='UTC')
    return parser.parse_args()


def return_metrics_values(line, metrics, time_format, columns_num):
    values = []
    fields = line.split(' ')
    timestamp = convert_to_timestamp(fields[0], time_format)
    for metric in metrics:
        if len(fields) != columns_num:
            values.append(-1)
        else:
            if timestamp > metric.now - metric.get_timeshift():
                # Getting highest ad lowest timestamp in file for metric
                if metric.end_timestamp == 0:
                    metric.end_timestamp = timestamp
                elif timestamp < metric.end_timestamp:
                    metric.start_timestamp = timestamp
                value = metric.estimate_columns_value(fields)
                values.append(value)
    return values


def get_metrics_last_value(line, metrics):
    fields = line.split()
    for metric in metrics:
        metric.last_value = metric.estimate_columns_value(fields)


def read_logfile_reverse(filename,
                         columns_num,
                         time_format,
                         metrics,
                         buf_size=8192):
    """
    A generator that returns the lines of a file in reverse order.
    Stops to read when has met timestamp bigger then desired period 
    
    returns False if file was not read completely
    """
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
                if buffer[-1] is not '\n':
                    lines[-1] += segment
                else:
                    yield return_metrics_values(segment, metrics, time_format,
                                                columns_num)
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                global_index += 1
                if lines[index]:
                    #if global_index == 1:
                    # get_metrics_last_value(lines[index], metrics)
                    yield return_metrics_values(lines[index], metrics,
                                                time_format, columns_num)

    if segment is not None:
        yield return_metrics_values(segment, metrics, time_format, columns_num)


def convert_to_timestamp(time_str, time_format):
    try:
        timestamp = int(
            time.mktime(time.strptime(time_str.split('+', 1)[0], time_format)))
    except ValueError:
        try:
            timestamp = int(time_str)
        except ValueError:
            timestamp = int(
                time.mktime(
                    time.strptime('-'.join(time_str.split('-')[:-1]),
                                  time_format)))
    return int(timestamp)


def main():
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(logging.StreamHandler())

    if args.time_zone:
        os.environ['TZ'] = args.time_zone
        time.tzset()

    file_was_readed = True

    # Read from the end of file until the timestamp is satisfying conditions
    data = read_logfile_reverse(
        args.file, args.columns_num, args.time_format, metrics=args.metric)
    for log_value in data:
        # Stop reading if next line has bigger timestamp as a required
        if not log_value:
            file_was_readed = log_value
            break
        else:
            for index, value in enumerate(log_value):
                if value != -1:
                    args.metric[index].values.append(value)

    # If the main file was read completely and there is arch flag then
    # check archive files for the presence of a timestamp satisfying condition
    if args.arch and file_was_readed:
        dir_path = os.path.dirname(os.path.realpath(args.file))
        archive_pattern = re.compile(r'{}\.\d+?\.gz'.format(args.file))
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                if archive_pattern.search(f):
                    archive_file = os.path.join(root, f)
                    logging.getLogger().debug(
                        'Parsing archive file: {}'.format(f))
                    with gzip.open(archive_file, 'rt', encoding='utf-8') as fh:
                        for line in fh:
                            fields = line.split()
                            if len(fields) != 5:
                                continue
                            fields[0] = convert_to_timestamp(
                                fields[0], args.time_format)
                            for metric in args.metric:
                                if fields[0] > (
                                        metric.now - metric.get_timeshift()):
                                    metric.values.append(
                                        metric.estimate_columns_value(fields))

    for metric in args.metric:
        template = args.prefix + '.{} {} ' + str(metric.now)
        print(template.format(metric.name, metric.get_metric_value()))


if __name__ == '__main__':
    main()
