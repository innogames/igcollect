#!/usr/bin/env python
#
# igcollect - PostgreSQL
#
# Copyright (c) 2017, InnoGames GmbH
#

from argparse import ArgumentParser
from time import time

from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ
from psycopg2.extras import RealDictCursor


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='postgres')
    parser.add_argument('--dbname', default='postgres')
    return parser.parse_args()


def main():
    args = parse_args()

    conn = connect(database=args.dbname)
    conn.set_session(
        isolation_level=ISOLATION_LEVEL_REPEATABLE_READ,
        readonly=True,
    )

    # To be formatted 3 times
    template = '{}.{{}}.{{{{}}}} {{{{}}}} {}'.format(args.prefix, int(time()))

    # Database statistics
    execute_and_print(conn, template.format('database'), (
        'SELECT pg_database_size(d.oid) as size,'
        '       s.numbackends,'
        '       s.xact_commit,'
        '       s.xact_rollback,'
        '       s.blks_read,'
        '       s.blks_hit,'
        '       s.tup_returned,'
        '       s.tup_fetched,'
        '       s.tup_inserted,'
        '       s.tup_updated,'
        '       s.tup_deleted,'
        '       s.conflicts,'
        '       s.temp_files,'
        '       s.temp_bytes,'
        '       s.deadlocks,'
        '       s.blk_read_time,'
        '       s.blk_write_time'
        '   FROM pg_database AS d'
        '       JOIN pg_stat_database AS s USING (datname)'
        '   WHERE d.datname = %s'
    ), (args.dbname,))

    # System table statistics
    execute_and_print(conn, template.format('tables'), (
        'SELECT sum(seq_scan) AS seq_scan,'
        '       sum(seq_tup_read) AS seq_tup_read,'
        '       sum(idx_scan) AS idx_scan,'
        '       sum(idx_tup_fetch) AS idx_tup_fetch,'
        '       sum(n_tup_ins) AS tup_ins,'
        '       sum(n_tup_upd) AS tup_upd,'
        '       sum(n_tup_del) AS tup_del,'
        '       sum(n_tup_hot_upd) AS tup_hot_upd,'
        '       sum(n_live_tup) AS live_tup,'
        '       sum(n_dead_tup) AS dead_tup,'
        '       sum(vacuum_count) AS vacuum_count,'
        '       sum(autovacuum_count) AS autovacuum_count,'
        '       sum(analyze_count) AS analyze_count,'
        '       sum(autoanalyze_count) AS autoanalyze_count'
        '   FROM pg_stat_all_tables'
    ))

    # Connection counts
    execute_and_print(conn, template.format('activity'), (
        "SELECT count(*) FILTER (WHERE state LIKE %s) AS active,"
        "       count(*) FILTER (WHERE state LIKE %s) AS idle,"
        "       count(*) FILTER (WHERE state LIKE %s) AS idle_in_transaction"
        '   FROM pg_stat_activity'
    ), ('active%', 'idle%', 'idle in transaction%'))


def execute_and_print(conn, template, query, query_vars=()):
    """Execute given query and return fetched results"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, query_vars)
        result = cursor.fetchall()

    for line in result:
        for key, value in line.items():
            if value is not None:
                print(template.format(key, value))
        break


if __name__ == '__main__':
    main()
