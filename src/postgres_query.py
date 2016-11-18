#!/usr/bin/env python
#
# igcollect - PostgreSQL query results
#
# This script executes a single query and prints the results.  The columns
# returned by the query are going to be appended to the given prefix.
# The query must return numeric values.
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function

from argparse import ArgumentParser
from time import time

import psycopg2
from psycopg2.extras import RealDictCursor


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='postgres_query')
    parser.add_argument('--dbname', default='postgres')
    parser.add_argument(
        '--query',
        required=True,
        action='append',
        dest='queries',
    )
    return parser.parse_args()


def main():
    """The main program"""
    args = parse_args()
    now = str(int(time()))

    with psycopg2.connect(database=args.dbname) as conn:
        conn.set_session(
            isolation_level=psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
            readonly=True,
        )

        for query in args.queries:
            for line in execute(conn, query):
                for key, value in line.items():
                    print(args.prefix + '.' + key, value, now)


def execute(conn, query):
    """Execute given query and return fetched results"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)

        return cursor.fetchall()


if __name__ == '__main__':
    main()
