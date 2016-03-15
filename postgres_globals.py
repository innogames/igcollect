#!/usr/bin/env python
#
# igcollect - PostgreSQL globals
#
# Copyright (c) 2016, InnoGames GmbH
#

import time

from libigcollect.postgres import get_prefix, get_user_databases, connect_and_execute

prefix = get_prefix()
user_databases = get_user_databases()

#
# Databases
#
template = prefix + "db.{0}.{1} {2} {3}"
query = """SELECT datname, datlastsysoid, datfrozenxid, datminmxid,
                  pg_database_size(oid) as size
           FROM pg_database
           WHERE datname NOT LIKE 'template%'"""
now = str(int(time.time()))

for line in connect_and_execute(query):
    datname = line.pop("datname")

    for key, value in line.items():
        if value != None:
            print(template.format(datname, key, value, now))

#
# Statistics by database system tables
#
for database in user_databases:
    template = prefix + "db." + database + ".stat_sys_tables.{0} {1} {2}"
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
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        for key, value in line.items():
            print(template.format(key, value, now))

#
# Statistics by database user tables
#
for database in user_databases:
    template = prefix + "db." + database + ".stat_user_tables.{0} {1} {2}"
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
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        for key, value in line.items():
            print(template.format(key, value, now))

#
# IO statistics by database system tables
#
for database in user_databases:
    template = prefix + "db." + database + ".statio_sys_tables.{0} {1} {2}"
    query = """SELECT sum(heap_blks_read) AS sum_heap_blks_read,
                      sum(heap_blks_hit) AS sum_heap_blks_hit,
                      sum(idx_blks_read) AS sum_idx_blks_read,
                      sum(idx_blks_hit) AS sum_idx_blks_hit,
                      sum(toast_blks_read) AS sum_toast_blks_read,
                      sum(toast_blks_hit) AS sum_toast_blks_hit,
                      sum(tidx_blks_read) AS sum_tidx_blks_read,
                      sum(tidx_blks_hit) AS sum_tidx_blks_hit
               FROM pg_statio_sys_tables"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        for key, value in line.items():
            print(template.format(key, value, now))

#
# IO statistics by database user tables
#
for database in user_databases:
    template = prefix + "db." + database + ".statio_user_tables.{0} {1} {2}"
    query = """SELECT sum(heap_blks_read) AS sum_heap_blks_read,
                      sum(heap_blks_hit) AS sum_heap_blks_hit,
                      sum(idx_blks_read) AS sum_idx_blks_read,
                      sum(idx_blks_hit) AS sum_idx_blks_hit,
                      sum(toast_blks_read) AS sum_toast_blks_read,
                      sum(toast_blks_hit) AS sum_toast_blks_hit,
                      sum(tidx_blks_read) AS sum_tidx_blks_read,
                      sum(tidx_blks_hit) AS sum_tidx_blks_hit
               FROM pg_statio_user_tables"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        for key, value in line.items():
            print(template.format(key, value, now))

#
# Tablespaces
#
template = prefix + "tablespace.{0}.{1} {2} {3}"
query = """SELECT spcname, pg_tablespace_size(oid) as size
           FROM pg_tablespace"""
now = str(int(time.time()))

for line in connect_and_execute(query):
    spcname = line.pop("spcname")

    for key, value in line.items():
        if value != None:
            print(template.format(spcname, key, value, now))

#
# Statistics by database
#
template = prefix + "db.{0}.stat.{1} {2} {3}"
query = """SELECT datname, numbackends, xact_commit, xact_rollback,
                  blks_read, blks_hit, tup_returned, tup_fetched,
                  tup_inserted, tup_updated, tup_deleted, conflicts,
                  temp_files, temp_bytes, deadlocks, blk_read_time,
                  blk_write_time
           FROM pg_stat_database
           WHERE datname NOT LIKE 'template%'"""
now = str(int(time.time()))

for line in connect_and_execute(query):
    datname = line.pop("datname")

    for key, value in line.items():
        if value != None:
            print(template.format(datname, key, value, now))

#
# Connection counts by database and connection state
#
template = prefix + "db.{0}.conn.{1} {2} {3}"
query = """SELECT datname, state, count(*) as count
           FROM pg_stat_activity
           GROUP BY datname, state"""
now = str(int(time.time()))

for line in connect_and_execute(query):
    print(template.format(
        line['datname'],
        line['state'].replace(' ', '_'),
        line['count'],
        now,
    ))

#
# Lock counts by database and lock mode
#
template = prefix + "db.{0}.lock.{1} {2} {3}"
query = """SELECT datname, mode, count(*) as count
           FROM pg_locks
           JOIN pg_database ON pg_locks.database = pg_database.oid
           GROUP BY datname, mode"""
now = str(int(time.time()))

for line in connect_and_execute(query):
    print(template.format(line['datname'], line['mode'], line['count'], now))

#
# Statistics of bgwriter process
#
template = prefix + "bgwriter.{0} {1} {2}"
query = """SELECT checkpoints_timed, checkpoints_req,
                  checkpoint_write_time, checkpoint_sync_time,
                  buffers_checkpoint, buffers_clean, maxwritten_clean,
                  buffers_backend, buffers_backend_fsync, buffers_alloc
           FROM pg_stat_bgwriter"""
now = str(int(time.time()))

for key, value in connect_and_execute(query)[0].items():
    if value != None:
        print(template.format(key, value, now))
