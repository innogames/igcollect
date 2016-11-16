#!/usr/bin/env python
#
# igcollect - Zookeeper
#
# Copyright (c) 2016, InnoGames GmbH
#

import time
import socket
from socket import gethostname

now = str(int(time.time()))
hostname = gethostname().replace('.', '_')

names = [
    "zk_avg_latency",
    "zk_max_latency",
    "zk_min_latency",
    "zk_packets_received",
    "zk_packets_sent",
    "zk_ephemerals_count",
    "zk_approximate_data_size",
    "zk_open_file_descriptor_count",
    "zk_max_file_descriptor_count",
    "zk_znode_count",
    "zk_watch_count"]

values = {}


def netcat(hostname, port, content):
    mntr = ""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    s.sendall(content)
    s.shutdown(socket.SHUT_WR)
    while True:
        data = s.recv(1024)
        if data == "":
            break
        # for line in data.split("\n"):
        #    print line
        mntr += data
    # print "Connection closed."
    s.close()
    return mntr

data = netcat("localhost", 2181, "mntr")

data = data.rstrip("\n")

for line in data.split("\n"):
    key, value = line.split("\t")
    values[key] = value

for value in names:
    # print "{0} : {1}".format(value,values[value])
    print "servers.{0}.software.zookeeper.{1} {2} {3}".format(hostname, value, values[value], now)
