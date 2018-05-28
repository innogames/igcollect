#!/usr/bin/env python
"""igcollect - MySQL Replication Delay

Copyright (c) 2017 InnoGames GmbH
"""

from argparse import ArgumentParser
from subprocess import check_output
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='mysql')
    parser.add_argument(
        '--database',
        type=str,
        required=True,
        help='Database to read timestamps from',
    )
    parser.add_argument(
        '--master-id',
        type=int,
        required=True,
        help='server_id of the writer of timestamps',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.seconds_behind_master.{} {} ' + str(int(time()))
    delay = check_output((
        '/usr/bin/pt-heartbeat',
        '--check',
        '--database={0}'.format(args.database),
        '--master-server-id={0}'.format(args.master_id)
    )).strip()

    # Make sure the command returned a proper value by casting it to float
    print(template.format(args.master_id, float(delay)))


if __name__ == '__main__':
    main()
