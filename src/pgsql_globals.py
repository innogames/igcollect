#!/usr/bin/env python
"""igcollect - PostgreSQL Globals

Copyright (c) 2016 InnoGames GmbH
"""

from argparse import ArgumentParser
from time import time

from libigcollect.postgres import get_user_databases, connect_and_execute


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='pgsql')
    return parser.parse_args()


def main():
    args = parse_args()
    user_databases = get_user_databases()

    # Databases
    template = args.prefix + '.db.{}.{} {} ' + str(int(time()))
    query = """SELECT datname, datlastsysoid, datfrozenxid, datminmxid,
                    pg_database_size(oid) as size
            FROM pg_database
            WHERE datname NOT LIKE 'template%'"""

    for line in connect_and_execute(query):
        datname = line.pop('datname')

        for key, value in line.items():
            if value is not None:
                print(template.format(datname, key, value))

    # Statistics by database system tables
    for database in user_databases:
        template = (
            args.prefix + '.db.' + database + '.stat_sys_tables.{} {} ' +
            str(int(time()))
        )
        query = """SELECT sum(seq_scan) AS sum_seq_scan,
                        sum(seq_tup_read) AS sum_seq_tup_read,
                        sum(idx_scan) AS sum_idx_scan,
                        sum(idx_tup_fetch) AS sum_idx_tup_fetch,
                        sum(n_tup_ins) AS sumn_tup_ins,
                        sum(n_tup_upd) AS sum_n_tup_upd,
                        sum(n_tup_del) AS sum_n_tup_del,
                        sum(n_tup_hot_upd) AS sum_n_tup_hot_upd,
                        sum(n_live_tup) AS sum_n_live_tup,
                        sum(n_dead_tup) AS sum_n_dead_tup,
                        sum(vacuum_count) AS sum_vacuum_count,
                        sum(autovacuum_count) AS sum_autovacuum_count,
                        sum(analyze_count) AS sum_analyze_count,
                        sum(autoanalyze_count) AS sum_autoanalyze_count
                FROM pg_stat_sys_tables"""

        for line in connect_and_execute(query, database):
            for key, value in line.items():
                print(template.format(key, value))

    # Statistics by database user tables
    for database in user_databases:
        template = (
            args.prefix + '.db.' + database + '.stat_user_tables.{} {} ' +
            str(int(time()))
        )
        query = """SELECT sum(seq_scan) AS sum_seq_scan,
                        sum(seq_tup_read) AS sum_seq_tup_read,
                        sum(idx_scan) AS sum_idx_scan,
                        sum(idx_tup_fetch) AS sum_idx_tup_fetch,
                        sum(n_tup_ins) AS sumn_tup_ins,
                        sum(n_tup_upd) AS sum_n_tup_upd,
                        sum(n_tup_del) AS sum_n_tup_del,
                        sum(n_tup_hot_upd) AS sum_n_tup_hot_upd,
                        sum(n_live_tup) AS sum_n_live_tup,
                        sum(n_dead_tup) AS sum_n_dead_tup,
                        sum(vacuum_count) AS sum_vacuum_count,
                        sum(autovacuum_count) AS sum_autovacuum_count,
                        sum(analyze_count) AS sum_analyze_count,
                        sum(autoanalyze_count) AS sum_autoanalyze_count
                FROM pg_stat_user_tables"""

        for line in connect_and_execute(query, database):
            for key, value in line.items():
                if value is not None:
                    print(template.format(key, value))

    # IO statistics by database system tables
    for database in user_databases:
        template = (
            args.prefix + '.db.' + database + '.statio_sys_tables.{} {} ' +
            str(int(time()))
        )
        query = """SELECT sum(heap_blks_read) AS sum_heap_blks_read,
                        sum(heap_blks_hit) AS sum_heap_blks_hit,
                        sum(idx_blks_read) AS sum_idx_blks_read,
                        sum(idx_blks_hit) AS sum_idx_blks_hit,
                        sum(toast_blks_read) AS sum_toast_blks_read,
                        sum(toast_blks_hit) AS sum_toast_blks_hit,
                        sum(tidx_blks_read) AS sum_tidx_blks_read,
                        sum(tidx_blks_hit) AS sum_tidx_blks_hit
                FROM pg_statio_sys_tables"""

        for line in connect_and_execute(query, database):
            for key, value in line.items():
                if value is not None:
                    print(template.format(key, value))

    # IO statistics by database user tables
    for database in user_databases:
        template = (
            args.prefix + '.db.' + database + '.statio_user_tables.{} {} ' +
            str(int(time()))
        )
        query = """SELECT sum(heap_blks_read) AS sum_heap_blks_read,
                        sum(heap_blks_hit) AS sum_heap_blks_hit,
                        sum(idx_blks_read) AS sum_idx_blks_read,
                        sum(idx_blks_hit) AS sum_idx_blks_hit,
                        sum(toast_blks_read) AS sum_toast_blks_read,
                        sum(toast_blks_hit) AS sum_toast_blks_hit,
                        sum(tidx_blks_read) AS sum_tidx_blks_read,
                        sum(tidx_blks_hit) AS sum_tidx_blks_hit
                FROM pg_statio_user_tables"""

        for line in connect_and_execute(query, database):
            for key, value in line.items():
                if value is not None:
                    print(template.format(key, value))

    # Tablespaces
    template = args.prefix + '.tablespace.{}.{} {} ' + str(int(time()))
    query = """SELECT spcname, pg_tablespace_size(oid) as size
            FROM pg_tablespace"""

    for line in connect_and_execute(query):
        spcname = line.pop('spcname')

        for key, value in line.items():
            if value is not None:
                print(template.format(spcname, key, value))

    # Statistics by database
    template = args.prefix + '.db.{}.stat.{} {} ' + str(int(time()))
    query = """SELECT datname, numbackends, xact_commit, xact_rollback,
                    blks_read, blks_hit, tup_returned, tup_fetched,
                    tup_inserted, tup_updated, tup_deleted, conflicts,
                    temp_files, temp_bytes, deadlocks, blk_read_time,
                    blk_write_time
            FROM pg_stat_database
            WHERE datname NOT LIKE 'template%'"""

    for line in connect_and_execute(query):
        datname = line.pop('datname')

        for key, value in line.items():
            if value is not None:
                print(template.format(datname, key, value))

    # Connection counts by database and connection state
    template = args.prefix + '.db.{}.conn.{} {} ' + str(int(time()))
    query = """SELECT datname, state, count(*) as count
            FROM pg_stat_activity
            GROUP BY datname, state"""

    for line in connect_and_execute(query):
        print(template.format(
            line['datname'], line['state'].replace(' ', '_'), line['count']
        ))

    # Lock counts by database and lock mode
    template = args.prefix + '.db.{}.lock.{} {} ' + str(int(time()))
    query = """SELECT datname, mode, count(*) as count
            FROM pg_locks
            JOIN pg_database ON pg_locks.database = pg_database.oid
            GROUP BY datname, mode"""

    for line in connect_and_execute(query):
        print(template.format(line['datname'], line['mode'], line['count']))

    # Statistics of bgwriter process
    template = args.prefix + '.bgwriter.{} {} ' + str(int(time()))
    query = """SELECT checkpoints_timed, checkpoints_req,
                    checkpoint_write_time, checkpoint_sync_time,
                    buffers_checkpoint, buffers_clean, maxwritten_clean,
                    buffers_backend, buffers_backend_fsync, buffers_alloc
            FROM pg_stat_bgwriter"""

    for key, value in connect_and_execute(query)[0].items():
        if value is not None:
            print(template.format(key, value))


if __name__ == '__main__':
    main()
