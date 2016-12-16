#!/usr/bin/env python
#
# igcollect - Mysql replication delay
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
import socket
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--database', dest='db', type=str, required=True, help='Database to read timestamps from')
parser.add_argument('-m', '--master-id', dest='id', type=int, required=True, help='server_id of the writer of timestamps')
args = parser.parse_args()

hostname = socket.gethostname().replace(".", "_")
now =  str(int(time.time()))

delay = subprocess.check_output(
    [
        '/usr/bin/pt-heartbeat',
        '--check',
        '--database={0}'.format(args.db),
        '--master-server-id={0}'.format(args.id)
    ]).strip()

try:
    float(delay)
    print('servers.{0}.software.mysql.status.seconds_behind_master {1} {2}'.format(hostname, delay, now))
except ValueError:
    pass
