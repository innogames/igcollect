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

import argparse
import time

import psycopg2
from psycopg2.extras import RealDictCursor


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', default='postgres_query')
    parser.add_argument('--dbname', default='postgres')
    parser.add_argument('--query', required=True)

    return vars(parser.parse_args())


def main(prefix, dbname, query):
    """The main program"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database=dbname):
        for key, value in line.items():
            print(prefix + '.' + key, value, now)


def connect_and_execute(query, database='postgres'):
    """Connect to database, execute given query and return fetched results"""

    with psycopg2.connect(database=database) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()


if __name__ == '__main__':
    main(**parse_args())
