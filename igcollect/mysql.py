#!/usr/bin/env python
"""igcollect - MySQL Status

Copyright (c) 2016 InnoGames GmbH
"""

try:
    from mysql.connector import connect
except ImportError:
    from MySQLdb import connect

from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='mysql')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--user')
    parser.add_argument('--password')
    parser.add_argument(
        '--unix-socket',
        default='/var/run/mysqld/mysqld.sock',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))

    db = connect(
        user=args.user,
        passwd=args.password,
        host=args.host,
        unix_socket=args.unix_socket,
    )
    cur = db.cursor()

    # Check for global status
    cur.execute('SHOW GLOBAL STATUS')
    for row in cur.fetchall():
        if row[1].isdigit():
            print(template.format('status', row[0], row[1]))

    cur.execute('SHOW VARIABLES')
    for row in cur.fetchall():
        if row[1].isdigit():
            print(template.format('variables', row[0], row[1]))

    # Find out how much space we can recover by Optimize
    sysdbs = {
        'information_schema',
        'mysql',
        'performance_schema',
        'sys',
        'test',
    }
    free = 0
    cur.execute('SHOW DATABASES')
    for row in cur.fetchall():
        if row[0] in sysdbs:
            continue
        cur.execute(
            'SELECT table_name, '
            'ROUND(data_free / 1024 / 1024), '
            'ROUND((data_length + index_length), 2) '
            'FROM information_schema.tables '
            'WHERE table_type = "BASE TABLE" '
            'AND table_schema = %s',
            [row[0]]
        )
        for value in cur.fetchall():
            print(template.format('table_size', '{}.{}'.format(row[0], value[0]), value[2]))
            free += value[1]
    print(template.format('status', 'optimize_freeable', free))


if __name__ == '__main__':
    main()
