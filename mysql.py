#!/usr/bin/env python
#
# igcollect - Mysql Status
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
import socket
import MySQLdb

hostname = socket.gethostname().replace(".", "_")
now =  str(int(time.time()))

db = MySQLdb.connect(user = 'root', host = 'localhost', read_default_file='/etc/mysql/my.cnf')
cur = db.cursor()

# Check for global status
cur.execute("show global status")
for row in cur.fetchall():
    if row[1].isdigit():
        print "servers.{0}.software.mysql.status.{1} {2} {3}".format(hostname, row[0], row[1], now)

cur.execute("show variables")
for row in cur.fetchall():
    if row[1].isdigit():
        print "servers.{0}.software.mysql.variables.{1} {2} {3}".format(hostname, row[0], row[1], now)

# Check information_schema tables
columns = (
    'table_schema', 'table_name', 'avg_row_length', 'data_length',
    'max_data_length', 'index_length', 'data_free'
)
query = 'select ' + ', '.join(columns) + ' from information_schema.tables'
cur.execute(query)
for row in cur.fetchall():
    for i, column in enumerate(columns[2:], start=2):
        print "servers.{0}.software.mysql.information_schema.tables.{1}.{2}.{3} {4} {5}".format(
            hostname, row[0], row[1].lower(), column, row[i], now)
