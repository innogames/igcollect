#!/usr/bin/env python
#
# igcollect - Mysql query results
#
# This script executes a single query and prints the results.  The columns
# returned by the query are going to be appended to the given prefix.
# The query must return numeric values.
#
# Copyright (c) 2017, InnoGames GmbH
#
from __future__ import print_function

from argparse import ArgumentParser
from time import time

from MySQLdb import connect

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='mysql_query')
    parser.add_argument('--dbname', default='mysql')
    parser.add_argument('--user', default='root')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--password', default='password')
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

    cnx = connect(
        user=args.user,
        passwd=args.password,
        host=args.host,
        db=args.dbname,
    )
    cur = cnx.cursor()
    for query in args.queries:
        cur.execute(query)
        if not cur.rowcount:
            raise Exception('No result')
        rows = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
        if args.key_column:
            items.extend(get_row_data(rows, args.key_column))
        else:
            items.extend(get_column_data(rows))

    for key, value in items:
        print(args.prefix + '.' + str(key), value, now)

    cur.close()
    cnx.close()


def get_column_data(rows):
    if len(rows) > 1:
        raise Exception('Multiple rows')
    for row in rows:
        return row.items()


def get_row_data(rows, key_column):
    first_row = rows[0]
    if key_column not in first_row:
        raise Exception('Key column is not there')
    if len(first_row) < 2:
        raise Exception('No column to print values')
    if len(first_row) > 2:
        raise Exception('More than 2 columns')

    for row in rows:
        key = row.pop(key_column)
        for value in row.values():
            yield key, value


if __name__ == '__main__':
    main()
