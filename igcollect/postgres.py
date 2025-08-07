#!/usr/bin/env python3
"""igcollect - PostgreSQL

Copyright (c) 2025 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time

from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ
from psycopg2.extras import RealDictCursor


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--prefix", default="postgres")
    parser.add_argument("--dbname", default="postgres")
    parser.add_argument("--extended", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    conn = connect(database=args.dbname)
    conn.set_session(
        isolation_level=ISOLATION_LEVEL_REPEATABLE_READ,
        readonly=True,
    )

    # Set a lock_timeout of 10s to avoid piling up queries in case something is locked for a longer time
    with conn.cursor() as cur:
        cur.execute("SET lock_timeout = 10000;")  # 10 seconds

    # Get PostgreSQL version, as some statistics are version dependent
    version = get_postgres_version(conn)

    # To be formatted 2 times
    template = '{}.{{}}.{{}} {{}} {}'.format(args.prefix, int(time()))
    # Database statistics
    for line in execute(conn, (
        'SELECT pg_database_size(d.oid) as size,'
        '       s.numbackends,'
        '       s.xact_commit,'
        '       s.xact_rollback,'
        '       s.blks_read,'
        '       s.blks_hit,'
        '       s.tup_returned,'
        '       s.tup_fetched,'
        '       s.tup_inserted,'
        '       s.tup_deleted,'
        '       s.tup_updated,'
        '       s.conflicts,'
        '       s.temp_files,'
        '       s.temp_bytes,'
        '       s.deadlocks,'
        '       s.blk_read_time,'
        '       s.blk_write_time'
        '   FROM pg_database AS d'
        '       JOIN pg_stat_database AS s USING (datname)'
        '   WHERE d.datname = %s'
    ), (args.dbname,)):
        for key, value in line.items():
            if value is not None:
                print(template.format('database', key, value))

    # Table statistics
    for line in execute(conn, (
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
    )):
        for key, value in line.items():
            if value is not None:
                print(template.format('tables', key, value))

    # Connection counts
    for line in execute(conn, (
        "SELECT state, count(*)"
        '   FROM pg_stat_activity'
        '   GROUP BY state'
    )):
        if line['state']:
            key = line['state'].replace(' ', '_')
            print(template.format('activity', key, line['count']))

    if args.extended:
        # Per relations statistics:
        rel_stat_tables = ['pg_stat_all_tables',
                           'pg_statio_all_tables',
                           'pg_stat_all_indexes',
                           'pg_statio_all_indexes',
                           ]
        for stat_table in rel_stat_tables:
            for line in execute(conn, (
                'SELECT * FROM {}'.format(stat_table)
            )):
                for key, value in line.items():
                    if (key not in ["schemaname",
                                    "relname",
                                    "relid",
                                    "pid",
                                    "indexrelname",
                                    "indexrelid",
                                    "last_archived_wal",
                                    ]
                            and value):
                        postfix = '{}.{}.{}'.format(stat_table,
                                                    line['schemaname'],
                                                    line['relname'],)
                        if 'indexrelname' in line:
                            postfix = '{}.{}.{}.{}'.format(stat_table,
                                                           line['schemaname'],
                                                           line['relname'],
                                                           line['indexrelname'],
                                                           )

                        # convert formatted timestamps to unix timestamps
                        if key in [
                            "last_analyze",
                            "last_autovacuum",
                            "last_autoanalyze",
                            "last_seq_scan",
                            "last_vacuum",
                            "last_idx_scan",
                            "last_archived_time",
                        ]:
                            value = int(value.timestamp())

                        print(template.format(postfix, key, value))

        # bgwriter (checkpoints)
        for line in execute(conn, (
                'SELECT * FROM pg_stat_bgwriter'
        )):
            for key, value in line.items():
                print(template.format('bgwriter', key, value))

        # table size
        for line in execute(conn, ('''
                SELECT c.relname, pg_total_relation_size(c.oid)
                FROM pg_class c
                LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'm') AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY pg_total_relation_size(c.oid) DESC;
        ''')):
            print(template.format('table_size', line['relname'], line['pg_total_relation_size']))

        # Autovacuum
        if version >= 170000:  # pg17 and above: max_dead_tuples->max_dead_tuple_bytes, num_dead_tuples->num_dead_item_ids
            vacuum_query = '''
                SELECT relid::regclass::text as table,
                    phase,
                    heap_blks_total,
                    heap_blks_scanned,
                    heap_blks_vacuumed,
                    index_vacuum_count,
                    max_dead_tuple_bytes,
                    num_dead_item_ids,
                    dead_tuple_bytes
                FROM pg_stat_progress_vacuum
                WHERE datname = %s
                '''
        else:
            vacuum_query = '''
                SELECT relid::regclass::text as table,
                    phase,
                    heap_blks_total,
                    heap_blks_scanned,
                    heap_blks_vacuumed,
                    index_vacuum_count,
                    max_dead_tuples,
                    num_dead_tuples
                FROM pg_stat_progress_vacuum
                WHERE datname = %s
                '''

        for line in execute(conn, vacuum_query, (args.dbname,)):
            postfix = '{}.{}.{}.{}'.format('vacuum',
                                           'tables',
                                           line['table'],
                                           line['phase'])
            for key, value in line.items():
                if key not in ['table', 'phase'] and value is not None:
                    print(template.format(postfix, key, value))

        # Autovacuum wraparound protection on tables
        # https://www.cybertec-postgresql.com/en/autovacuum-wraparound-protection-in-postgresql/
        for line in execute(conn, ('''
                SELECT
                    oid::regclass::text AS table,
                    least(
                        (SELECT setting::int
                        FROM    pg_settings
                        WHERE   name = 'autovacuum_freeze_max_age')
                                        - age(relfrozenxid),
                        (SELECT setting::int
                        FROM    pg_settings
                        WHERE   name = 'autovacuum_multixact_freeze_max_age')
                                        - mxid_age(relminmxid)
                        ) AS value
                FROM    pg_class
                WHERE   relfrozenxid != 0
                AND oid > 16384''')):
            postfix = '{}.{}.{}'.format('vacuum',
                                        'tables',
                                        line['table'])
            print(template.format(postfix, 'tx_before_wraparound_vacuum',
                                  line['value']))

        # Locks
        for line in execute(conn, (
                'SELECT mode, count(1) as value FROM pg_locks GROUP BY mode'
        )):
            postfix = '{}.{}'.format('database',
                                     'locks')
            print(template.format(postfix, line['mode'], line['value']))

        # Archiver
        for line in execute(conn, (
                'SELECT * FROM pg_stat_archiver'
        )):
            postfix = '{}.{}.{}'.format('database',
                                        'wal',
                                        'archiver')
            for key, value in line.items():
                if value is not None:
                    print(template.format(postfix, key, value))

         # Replication
        for line in execute(conn, (
                'SELECT client_hostname as hostname, '
                'EXTRACT(EPOCH FROM replay_lag) as replay_lag '
                'FROM pg_stat_replication'
        )):
            postfix = '{}.{}'.format('replication',
                                     'replay_lag',
                                    )
            print(template.format(postfix, line['hostname'].replace('.', '_'),
                                  line['replay_lag']))

def get_postgres_version(conn) -> int:
    """Fetch the PostgreSQL version number."""
    version = execute(conn, "SHOW server_version_num")[0]['server_version_num']
    return int(version)


def execute(conn, query, query_vars=()):
    """Execute given query and return fetched results"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, query_vars)
        return cursor.fetchall()


if __name__ == "__main__":
    main()
