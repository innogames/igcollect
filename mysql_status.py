#!/usr/bin/env python
#
# igcollect - Mysql Status "show status"
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
import socket
import MySQLdb

hostname = socket.gethostname().replace(".", "_")
now =  str(int(time.time()))

db = MySQLdb.connect(host = 'localhost', read_default_file='/etc/mysql/my.cnf')
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
