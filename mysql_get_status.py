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

db = MySQLdb.connect(host = 'localhost')
cur = db.cursor()
cur.execute("show status")
now =  str(int(time.time()))

for row in cur.fetchall():
    if row[1].isdigit():
      print "servers.{0}.software.mysql.status.{1} {2} {3}".format(hostname, row[0], row[1], now)
   
