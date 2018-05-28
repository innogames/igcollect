#!/usr/bin/env python
"""igcollect - PostgreSQL Query Results

This script executes a single query and prints the results.  The columns
returned by the query are going to be appended to the given prefix.
The query must return numeric values.

Copyright (c) 2016 InnoGames GmbH
"""

from __future__ import print_function

from argparse import ArgumentParser
from time import time

from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ
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
    parser.add_argument('--key-column')
    return parser.parse_args()


def main():
    """The main program"""
    args = parse_args()
    items = []
    now = str(int(time()))

    with connect(database=args.dbname) as conn:
        conn.set_session(
            isolation_level=ISOLATION_LEVEL_REPEATABLE_READ,
            readonly=True,
        )

        for query in args.queries:
            rows = execute(conn, query)
            if len(rows) == 0:
                raise Exception('No result')
            items.extend(
                get_row_data(args.key_column, rows) if args.key_column
                else get_column_data(rows)
            )

    for key, value in items:
        print(args.prefix + '.' + key, value, now)


def execute(conn, query):
    """Execute given query and return fetched results"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)

        return cursor.fetchall()


def get_column_data(rows):
    if len(rows) > 1:
        raise Exception('Multiple rows')
    for row in rows:
        return row.items()


def get_row_data(key_column, rows):
    first_row = rows[0]
    if key_column not in first_row:
        raise Exception('Key column is not there')
    if len(first_row) == 1:
        raise Exception('No column to print values')
    if len(first_row) > 2:
        raise Exception('More than 2 columns')

    for row in rows:
        key = row.pop(key_column)
        for value in row.values():
            yield key, value


if __name__ == '__main__':
    main()
