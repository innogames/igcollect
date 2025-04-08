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

from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime, timezone
import gzip
import logging
import os
import re
from os.path import exists
from typing import Any, List, Optional


@dataclass
class Metric:

    DEFINITION_LENGTH = 4

    definition: str
    name: Optional[str] = None
    column: Optional[str] = None
    function: Optional[str] = None
    period: Optional[str] = None
    values: list[float] = field(default_factory=list)
    last_value: int = 0

    def __post_init__(self):
        if ":" not in self.definition:
            raise ValueError("Invalid definition")
        metric_definition = self.definition.split(":")
        if len(metric_definition) == self.DEFINITION_LENGTH:
            self.name, self.column, self.function, self.period = metric_definition
        else:
            raise ValueError("Invalid metric definition")
        if self.period:
            pattern = r"^\d+[sminhd]$"
            if not re.match(pattern, self.period):
                raise ValueError("Invalid period")

    @property
    def timeshift(self) -> int:
        if not self.period:
            return 0
        units = [
            ('s', 1),
            ('min', 60),
            ('h', 60 * 60),
            ('d', 60 * 60 * 24),
        ]
        for unit, multiplier in units:
            if self.period.endswith(unit):
                return int(self.period[:-len(unit)]) * multiplier
        return 0

    def apply_function_to_values(self) -> Any:

        if self.function is None:
            raise ValueError("Function is not defined")
        function = self.function.split('_')
        logging.debug('Calling function %s with arguments %s', function[0], function[1:])
        func = getattr(self, function[0], None)
        if func and function[1:]:
            return func(*function[1:])
        return func

    @property
    def value(self):
        return self.apply_function_to_values()

    @property
    def sum(self) -> float:
        return sum(self.values)

    @property
    def count(self, v: int = 0) -> int:
        return sum(1 for x in self.values if x >= v)

    def percentage(self, *args) -> float:
        v = int(args[0]) if args else 0
        return sum(1 for x in self.values if x >= v) / len(self.values) * 100

    @property
    def mean(self):
        return sum(self.values) / len(self.values)

    @property
    def min(self):
        return min(self.values)

    @property
    def max(self):
        return max(self.values)

    @property
    def frequency(self) -> float:
        return self.count / self.timeshift

    @property
    def speed(self):
        return self.sum / self.timeshift

    @property
    def median(self):
        sorted_list = sorted(self.values)
        i = len(sorted_list)
        if not i % 2:
            return (sorted_list[(i // 2) - 1] + sorted_list[i // 2]) / 2
        return sorted_list[i // 2]

    @property
    def distribution(self) -> dict[int, int]:
        d = {}
        uniq_values = set(self.values)
        for v in uniq_values:
            d[int(v)] = self.values.count(v)
        return d

    def calculate(self, fields: List[str]):
        arr = [
            s for s in self.column if s.isdigit() or s in ['/', '*', '+', '-']
        ]
        result = 0
        for index, value in enumerate(arr):
            try:
                if value.isdigit() and result == 0:
                    result += float(self._extract_digits(fields[int(value)]))
                elif value == '/':
                    result = result / float(self._extract_digits(fields[int(arr[index + 1])]))
                elif value == '*':
                    result = result * float(self._extract_digits(fields[int(arr[index + 1])]))
                elif value == '+':
                    result = result + float(self._extract_digits(fields[int(arr[index + 1])]))
                elif value == '-':
                    result = result - float(self._extract_digits(fields[int(arr[index + 1])]))
            except ZeroDivisionError:
                result = 0
        self.values.append(result)

    def _extract_digits(self, s: str) -> str:
        if s.isdigit():
            return s
        return ''.join(re.findall(r'\d+', s))


@dataclass
class LogFileAnalyzer:
    filename: str
    timestamp_column: int
    columns: int
    metrics: List[Metric]

    include_archived: bool = False
    timestamp_format: str = '%Y-%m-%dT%H:%M:%S%z'
    buffer_size: int = 8096

    def __post_init__(self):
        self.metrics = [Metric(definition) for definition in self.metrics]
        if not self.metrics:
            raise ValueError('No metrics defined')
        if not exists(self.filename):
            raise FileNotFoundError(f"File {self.filename} does not exist")

    def _convert_to_timestamp(self, timestamp_string: str) -> int:
        """
        Disclamer about timezone part:
            if time_format doesn't specify timezone position, time tuple is treated
            as local
        """
        # When using Java17 we are seeing higher decimal fractions on the dates
        # that Python isn't able to handle.   We need to make sure that the
        # decimal fraction part is only 6 digits long.
        # The regexp replaces a 9 digit number with a 6 digit one
        # time_str example: '2022-05-25T12:05:15.654320355Z'
        _timestamp_string = timestamp_string.split('.', 1)
        if len(_timestamp_string) > 1 and len(_timestamp_string[1]) > 7:
            _timestamp_string[1] = re.sub(r'^([0-9]{6})[0-9]{3}(Z)?', r'\1\2', _timestamp_string[1])
            timestamp_string = '.'.join(_timestamp_string)
        try:

            # Python cannot parse ISO8601 dates with suffix Z for UTC which is a
            # valid representation so we need to help it in advance.
            if self.timestamp_format.endswith('z') and timestamp_string.endswith('Z'):
                timestamp_string = timestamp_string[:-1] + '+0000'

            # We have seen some wrong formats returning ISO8601 dates with suffix Z
            # with a colon separated e.g. +01:00 this needs to be fixed.
            if self.timestamp_format.endswith('z') and timestamp_string[-3] == ':':
                timestamp_string = ''.join(timestamp_string.rsplit(':', 1))
            timestamp: float = datetime.strptime(timestamp_string, self.timestamp_format).timestamp()
        except ValueError:
            logging.getLogger().debug('Error parsing timestamp %s', timestamp_string)
            timestamp = int(timestamp_string)
        return int(timestamp)


    def _get_metrics_last_value(self, line: str):
        fields = line.split()
        for metric in self.metrics:
            metric.last_value = metric.calculate(fields)


    def _get_metrics_values(
        self, segment: str
    ):
        now = int(datetime.now().timestamp())
        fields = segment.split()
        if self.columns and len(fields) != self.columns:
            return True
        timestamp = self._convert_to_timestamp(fields[self.timestamp_column])
        for metric in self.metrics:
            if timestamp > now - metric.timeshift:
                metric.calculate(fields)
            else:
                return False
        return True

    def read_reverse(self):
        with open(self.filename, encoding='utf-8') as fh:
            global_index = 0
            segment = None
            offset = 0
            fh.seek(0, os.SEEK_END)
            file_size = remaining_size = fh.tell()
            while remaining_size > 0:
                offset = min(file_size, offset + self.buffer_size)
                fh.seek(file_size - offset)
                buffer = fh.read(min(remaining_size, self.buffer_size))
                remaining_size -= self.buffer_size
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
                        yield self._get_metrics_values(segment)
                segment = lines[0]
                for index in range(len(lines) - 1, 0, -1):
                    global_index += 1
                    if lines[index]:
                        if global_index == 1:
                            self._get_metrics_last_value(lines[index])
                        yield self._get_metrics_values(lines[index])
        if segment is not None:
            yield self._get_metrics_values(segment)

    def _parse_archived_files(self):
        archive_pattern = re.compile(r'{}\.1\.gz'.format(self.filename))
        for root, _, files in os.walk(os.path.dirname(self.filename)):
            for file in files:
                if archive_pattern.match(file):
                    archive_file = os.path.join(root, file)
                    logging.getLogger().debug('Parsing archive file: {archive_file}')
                    with gzip.open(archive_file, 'rt', encoding='utf-8') as fh:
                        for line in fh:
                            self._get_metrics_values(line)

    def parse(self):
        file_was_readed = False
        for data in self.read_reverse():
            if not data:
                break
            file_was_readed = True
        if file_was_readed and self.include_archived:
            self._parse_archived_files()




def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='logfile_values')
    parser.add_argument('--file', default='/var/log/messages')
    parser.add_argument('--columns', default=0, type=int)
    parser.add_argument('--metric', type=str, nargs='+')
    parser.add_argument('--timestamp-column', default=0, type=int)
    parser.add_argument(
        '--timestamp-format', default='%Y-%m-%dT%H:%M:%S%z',
        help='If timezone is not specified, time string is treated as '
        'local time',
    )
    parser.add_argument('--arch', action='store_true')
    parser.add_argument('--debug', '-d', action='store_true')
    args = parser.parse_args()
    return args



def main():
    args = parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger().addHandler(logging.StreamHandler())

    log_file_analyzer = LogFileAnalyzer(
        filename=args.file,
        timestamp_column=args.timestamp_column,
        columns=args.columns,
        metrics=args.metric,
        timestamp_format=args.timestamp_format,
        include_archived=args.arch,
    )
    current_timestamp: int = int(datetime.now(timezone.utc).timestamp())
    log_file_analyzer.parse()
    for metric in log_file_analyzer.metrics:
        print(f"{args.prefix}.{metric.name} {metric.value} {current_timestamp}")


if __name__ == '__main__':
    main()
