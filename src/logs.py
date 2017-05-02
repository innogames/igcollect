#!/usr/bin/env python
#
# logfile_schema.py
#
# Copyright (c) 2016, InnoGames GmbH
#

"""
logfile_schema.py -- a python script to find messages within timeshift

This script is capable of scanning log files for a given regex for a message
and then compare them by a given time format if they are within a given
timeshift.

Imagine for example you want to scan a log file every 15 minutes for errors and
see how many errors occur and how many duplicates you have.

logfile_schema.py myfile.log 15m "([0-9]{2}-?){3} ([0-9]{2}:?){3}"
                  "%y-%m-%d %H:%M:%S" "(\[ERROR\].*)" --verbose
"""

import re
import logging
import hashlib
import argparse
import datetime

from os import environ
from os.path import isfile, expanduser
from time import time, tzset


def parse_args():
    """Parse arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument('file',
                        help='path to log file.')
    parser.add_argument('timeshift',
                        help='go e.g. 15m back in time from now.')
    parser.add_argument('time_regex',
                        help='e.g. ([0-9]{2}-?){3} ([0-9]{2}:?){3}')
    parser.add_argument('time_format',
                        help='e.g. %%y-%%m-%%d %%H:%%M:%%S')
    parser.add_argument('message_regex',
                        help='e.g. ([ERROR].*)')
    parser.add_argument('--prefix', default='logs')
    parser.add_argument('--timezone', '-z',
                        help='overwrite system timezone e.g. Europe/Berlin')
    parser.add_argument('--unique', '-u', action='store_true',
                        help='print number of unique events matching.')
    parser.add_argument('--total', '-t', action='store_true',
                        help='print number of total events matching.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='print total and unique and with pretty text.')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='enable debug output - useful to see regex match')

    return parser.parse_args()


def main():
    """Parse logfile and return result"""
    args = parse_args()

    if args.timezone:
        environ['TZ'] = args.timezone
        tzset()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.getLogger().addHandler(logging.StreamHandler())
    errors = dict()
    errors_total = 0
    timeshift = get_datetime_timeshift(args.timeshift)

    logging.getLogger().debug('matchings logs since %s', timeshift)

    if isfile(expanduser(args.file)):
        with open(args.file, mode='r') as f:

            # @TODO maybe it is possible to read file backwards and stop if
            # timeshift is exceeded so that we do not have to parse the
            # complete file every run.
            for line in f:
                logging.getLogger().debug('parsing line %s', line)
                time_string, message_string = get_datetime_and_message(
                    line,
                    args.time_regex,
                    args.time_format,
                    args.message_regex
                )

                if (
                    (time_string and message_string) and
                    (time_string >= timeshift)
                ):
                    logging.getLogger().debug(
                        'message is in time range: evaluating'
                    )
                    message_hash = hashlib.md5(
                        message_string.encode('utf-8')
                    ).hexdigest()
                    logging.getLogger().debug(
                        'hash for message is %s', message_hash
                    )

                    if message_hash not in errors:
                        logging.getLogger().debug(
                            'new message %s', message_hash
                        )
                        errors[message_hash] = 1
                    else:
                        logging.getLogger().debug(
                            'found message %s', message_hash
                        )
                        errors[message_hash] += 1

    errors_unique = len(errors)
    for matches in errors.values():
        errors_total += matches

    if args.verbose:
        print('{} unique errors'.format(errors_unique))
        print('{} errors total'.format(errors_total))
        print('timeshift {}'.format(timeshift))
    else:
        timestamp = str(int(time()))
        filename = args.file.replace('.', '_').lower().rsplit('/').pop()
        metric_path = '{}.{}'.format(args.prefix, filename)

        if args.total:
            print('{} {} {}'.format(metric_path, errors_total, timestamp))
        if args.unique:
            print('{} {} {}'.format(metric_path, errors_unique, timestamp))


def get_datetime_timeshift(timeshift):
    """Parse timehift into datetime -> datetime"""
    value = int(timeshift[:-1])
    unit = timeshift[-1].lower()
    now = datetime.datetime.fromtimestamp(time())

    if unit == 's':
        return now - datetime.timedelta(seconds=value)
    elif unit == 'm':
        return now - datetime.timedelta(minutes=value)
    elif unit == 'h':
        return now - datetime.timedelta(hours=value)
    elif unit == 'd':
        return now - datetime.timedelta(days=value)
    else:
        return datetime.datetime.fromtimestamp(0)


def get_datetime_and_message(line, time_regex, time_format, message_regex):
    """Parse datetime and message matching schema -> datetime, str"""
    time_string = None
    message_string = None

    logging.getLogger().debug(
        'searching for regex %s in %s', time_regex, line
    )
    time_match = re.search(time_regex, line)
    if time_match and len(time_match.groups()):
        raw_string = time_match.group(0)
        logging.getLogger().debug('match group is %s', raw_string)
        try:
            time_string = datetime.datetime.strptime(raw_string, time_format)
            logging.getLogger().debug('parsed time is %s', time_string)
        except ValueError:
            logging.getLogger().error(
                'can not parse time %s with time regex %s', raw_string,
                time_format
            )

        # makes only sense to continue and parse message_string fi we have a
        # time_string otherwise we could not compare it to timeshift.
        logging.getLogger().debug(
            'searching for regex %s in %s', message_regex, line
        )
        message_match = re.search(message_regex, line)
        if message_match and len(message_match.groups()):
            message_string = message_match.group(0)
            logging.getLogger().debug('match group is %s', message_string)

    return time_string, message_string


if __name__ == '__main__':
    main()
