#!/usr/bin/env python
#
# igcollect library - PostgreSQL routines
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


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

    conn = connect(database=database)

    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)

        return cursor.fetchall()
    finally:
        conn.close()
