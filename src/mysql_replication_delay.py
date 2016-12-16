#!/usr/bin/env python
#
# igcollect - MySQL replication delay
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from socket import gethostname
from subprocess import check_output
from time import time


def parse_args():
    parser = ArgumentParser()
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
    hostname = gethostname().replace('.', '_')
    now = int(time())
    template = 'servers.{}.software.mysql.status.seconds_behind_master {} {}'
    delay = check_output((
        '/usr/bin/pt-heartbeat',
        '--check',
        '--database={0}'.format(args.database),
        '--master-server-id={0}'.format(args.master_id)
    )).strip()

    # Make sure the command returned a proper value by casting it to float
    print(template.format(hostname, float(delay), now))


if __name__ == '__main__':
    main()
