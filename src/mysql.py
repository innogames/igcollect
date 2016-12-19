#!/usr/bin/env python
#
# igcollect - Mysql Status
#
# Copyright (c) 2016, InnoGames GmbH
#

import MySQLdb
from argparse import ArgumentParser
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='mysql')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))

    db = MySQLdb.connect(
        user='root',
        host='localhost',
        read_default_file='/etc/mysql/my.cnf',
    )
    cur = db.cursor()

    # Check for global status
    cur.execute('show global status')
    for row in cur.fetchall():
        if row[1].isdigit():
            print(template.format('status', row[0], row[1]))

    cur.execute('show variables')
    for row in cur.fetchall():
        if row[1].isdigit():
            print(template.format('variables', row[0], row[1]))

    # Find out how much space we can recover by Optimize
    sysdbs = {
        'information_schema',
        'performance_schema',
        'mysql',
        'sys',
        'test',
    }
    free = 0
    cur.execute('SHOW DATABASES')
    for row in cur.fetchall():
        if row[0] in sysdbs:
            continue
        cur.execute(
            'SELECT round(DATA_FREE / 1024 / 1024) '
            'FROM information_schema.tables '
            'WHERE TABLE_SCHEMA = %s AND DATA_FREE > 0',
            [row[0]]
        )
        for value in cur.fetchall():
            free += value[0]
    print(template.format('status', 'optimize_freeable', free))


if __name__ == '__main__':
    main()
