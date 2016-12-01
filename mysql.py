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
# Find out how much space we can recover by Optimize
sysdbs=['information_schema', 'performance_schema', 'mysql', 'sys', 'test']
free = 0
cur.execute("SHOW DATABASES")
for row in cur.fetchall():
    if row[0] in sysdbs:
        continue
    cur.execute('select round(DATA_FREE/1024/1024) from information_schema.tables where TABLE_SCHEMA=%s and DATA_FREE>0', [row[0]])
    for value in cur.fetchall():
        free += value[0]
print "servers.{0}.software.mysql.status.optimize_freeable {1} {2}".format(hostname, free, now)
