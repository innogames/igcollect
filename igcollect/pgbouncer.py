#!/usr/bin/env python
"""igcollect - PgBouncer

Copyright (c) 2018 InnoGames GmbH
"""

import psycopg2

from time import time
from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--host',
        help='PostgreSQL pgbouncer host (default: localhost)',
        default='localhost',
    )
    parser.add_argument(
        '--user',
        help='PostgreSQL db user to login (default: stats)',
        default='stats',
    )
    parser.add_argument(
        '--password',
        help='PostgreSQL db user password to login',
    )
    parser.add_argument(
        '--port',
        help='PostgreSQL pgbouncer pool port (default: 6432)',
        default=6432,
    )
    parser.add_argument(
        '--dbs',
        help='PostgreSQL pgbouncer db to gather pool metrics from',
        nargs='+',
    )
    parser.add_argument(
        '--prefix',
        help='Graphite metric path prefix for stats (default: pgbouncer)',
        default='pgbouncer',
    )

    return parser.parse_args()


def main():
    args = parse_args()

    dsn = "host={} user={} password={} port={} dbname=pgbouncer".format(
        args.host, args.user, args.password, args.port
    )
    conn = psycopg2.connect(dsn)
    conn.set_session(autocommit=True)
    cur = conn.cursor()
    timestamp = str(int(time()))

    # General statistics per pool
    stats_pools = [
        'database', 'user', 'cl_active', 'cl_waiting', 'cl_cancel_req',
        'sv_active', 'sv_idle', 'sv_used', 'sv_tested', 'sv_login', 'maxwait',
        'maxwait_us', 'pool_mode',
    ]
    cur.execute('SHOW POOLS')
    for row in cur.fetchall():
        if (args.dbs and row[0] in args.dbs) or (args.dbs is None):
            for col, value in list(zip(stats_pools, row))[2:]:
                print('{0}.{1}.{2}.{3} {4} {5}'.format(
                    args.prefix,
                    'pool',
                    row[0],
                    col,
                    value,
                    timestamp
                ))

    # Detailed statistics per pool
    stats_data = [
        'database', 'total_xact_count', 'total_query_count', 'total_received',
        'total_sent', 'total_xact_time', 'total_query_time', 'total_wait_time',
        'avg_xact_count', 'avg_query_count', 'avg_recv', 'avg_sent',
        'avg_xact_time', 'avg_query_time', 'avg_wait_time',
    ]
    cur.execute('SHOW STATS')
    for row in cur.fetchall():
        if (args.dbs and row[0] in args.dbs) or (args.dbs is None):
            for col, value in list(zip(stats_data, row))[1:]:
                print('{0}.{1}.{2}.{3} {4} {5}'.format(
                    args.prefix,
                    'stat',
                    row[0],
                    col,
                    value,
                    timestamp
                ))

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
