#!/usr/bin/env python
#
# igcollect - PostgreSQL objects
#
# Copyright (c) 2016, InnoGames GmbH
#

import time

from libigcollect.postgres import (
    get_prefix,
    get_user_databases,
    connect_and_execute,
)

prefix = get_prefix()
user_databases = get_user_databases()

#
# Database tables
#
for database in user_databases:
    template = prefix + "db." + database + ".table.{0}.{1}.{2} {3} {4}"
    query = """SELECT nspname, relname, relpages, reltuples, relfrozenxid,
                      pg_table_size(pg_class.oid) as size,
                      pg_indexes_size(pg_class.oid) as index_size
               FROM pg_class
               JOIN pg_namespace ON relnamespace = pg_namespace.oid
               WHERE relkind = 'r'"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        nspname = line.pop("nspname")
        relname = line.pop("relname")

        for key, value in line.items():
            if value is not None:
                print(template.format(nspname, relname, key, value, now))

#
# Detailed relation size by database tables
#
for database in user_databases:
    template = prefix + "db." + database + \
        ".table.{0}.{1}.rel_size.{2} {3} {4}"
    query = """SELECT nspname, relname, fname,
                      pg_relation_size(pg_class.oid, fname) as rel_size
               FROM pg_class
               JOIN pg_namespace ON relnamespace = pg_namespace.oid
               CROSS JOIN (VALUES ('main'), ('fsm'), ('vm'), ('init')) AS fork(fname)
               WHERE relkind = 'r'"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        print(template.format(line['nspname'], line['relname'],
                              line['fname'], line['rel_size'], now))

#
# Statistics by database user tables
#
for database in user_databases:
    template = prefix + "db." + database + ".table.{0}.{1}.stat.{2} {3} {4}"
    query = """SELECT schemaname, relname, seq_scan, seq_tup_read, idx_scan,
                      idx_tup_fetch, n_tup_ins, n_tup_upd, n_tup_del,
                      n_tup_hot_upd, n_live_tup, n_dead_tup, vacuum_count,
                      autovacuum_count, analyze_count, autoanalyze_count
               FROM pg_stat_user_tables"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        schemaname = line.pop("schemaname")
        relname = line.pop("relname")

        for key, value in line.items():
            if value is not None:
                print(template.format(schemaname, relname, key, value, now))

#
# IO statistics by database user tables
#
for database in user_databases:
    template = prefix + "db." + database + ".table.{0}.{1}.statio.{2} {3} {4}"
    query = """SELECT schemaname, relname, heap_blks_read, heap_blks_hit,
                      idx_blks_read, idx_blks_hit, toast_blks_read,
                      toast_blks_hit, tidx_blks_read, tidx_blks_hit
               FROM pg_statio_user_tables"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        schemaname = line.pop("schemaname")
        relname = line.pop("relname")

        for key, value in line.items():
            if value is not None:
                print(template.format(schemaname, relname, key, value, now))

#
# Indexes on database tables
#
for database in user_databases:
    template = prefix + "db." + database + \
        ".table.{0}.{1}.index.{2}.{3} {4} {5}"
    query = """SELECT nspname, table_class.relname,
                      index_class.relname AS indexrelname,
                      index_class.relpages,
                      pg_relation_size(index_class.oid) as size
               FROM pg_index
               JOIN pg_class AS index_class ON indexrelid = index_class.oid
               JOIN pg_class AS table_class ON indrelid = index_class.oid
               JOIN pg_namespace ON table_class.relnamespace = pg_namespace.oid"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        nspname = line.pop("nspname")
        relname = line.pop("relname")
        indexrelname = line.pop("indexrelname")

        for key, value in line.items():
            if value is not None:
                print(template.format(nspname, relname, indexrelname,
                                      key, value, now))

#
# IO statistics by user indexes on database tables
#
for database in user_databases:
    template = prefix + "db." + database + \
        ".table.{0}.{1}.index.{2}.statio.{3} {4} {5}"
    query = """SELECT schemaname, relname, indexrelname, idx_blks_read,
                      idx_blks_hit
               FROM pg_statio_user_indexes"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        schemaname = line.pop("schemaname")
        relname = line.pop("relname")
        indexrelname = line.pop("indexrelname")

        for key, value in line.items():
            if value is not None:
                print(template.format(schemaname, relname, indexrelname,
                                      key, value, now))

#
# IO statistics by database sequences
#
for database in user_databases:
    template = prefix + "db." + database + \
        ".sequence.{0}.{1}.statio.{2} {3} {4}"
    query = """SELECT schemaname, relname, blks_read, blks_hit
               FROM pg_statio_all_sequences"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        schemaname = line.pop("schemaname")
        relname = line.pop("relname")

        for key, value in line.items():
            if value is not None:
                print(template.format(schemaname, relname, key, value, now))

#
# Statistics by database user functions
#
for database in user_databases:
    template = prefix + "db." + database + ".function.{0}.{1}.stat.{2} {3} {4}"
    query = """SELECT schemaname, funcname, calls, total_time, self_time
               FROM pg_stat_user_functions"""
    now = str(int(time.time()))

    for line in connect_and_execute(query, database):
        schemaname = line.pop("schemaname")
        funcname = line.pop("funcname")

        for key, value in line.items():
            if value is not None:
                print(template.format(schemaname, funcname, key, value, now))
