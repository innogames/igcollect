#!/usr/bin/env python
#
# Graphite PostgreSQL Service Data Collector
#
# Copyright (c) 2015, InnoGames GmbH
#

from __future__ import print_function
import socket, psycopg2, psycopg2.extras

def get_prefix():
    """The prefix for the pgsql data collectors"""

    hostname = socket.gethostname().replace('.', '_')

    return "servers." + hostname + ".software.pgsql."

def get_user_databases():
    """Prepare the user database list

    postgres is the default database created by initdb, sandbox is
    the standard database name on InnoGames to store only the schema
    of the main database.  We are not going to bother collection stats
    of user objects in those databases.
    """

    query = """SELECT datname
               FROM pg_database
               WHERE datname NOT LIKE 'template%'
               AND datname NOT IN ('postgres', 'sandbox')"""

    return [line['datname'] for line in connect_and_execute(query)]

def connect_and_execute(query, database='postgres'):
    """Connect to database, execute given query and return fetched results"""

    conn = psycopg2.connect(database=database)

    try:
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query)

        return cursor.fetchall()
    finally:
        conn.close()
