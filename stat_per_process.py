#!/usr/bin/env python
#
# igcollect - process stat
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
import subprocess as sp
import sys
import socket
import time
import os.path

def get_process_list(config_file):
    content = ''
    if os.path.isfile(config_file):
        with open(config_file) as f:
            content = f.readlines()
    return content


def get_process_data(process_name):
    try:
        pid = sp.check_output(['pgrep', '-f', process_name])
        process_data = sp.check_output(['ps', '-p', pid.replace('\n',''), '-o', 'pcpu,pmem']).split('\n')
        process_data_split = process_data[1].strip().split(' ')
        return process_data_split[0], process_data_split[1]
    except:
        return False, False


hostname = socket.gethostname().replace('.','_')
now = str(int(time.time()))
graphite_data = ''

for process_name in get_process_list('/etc/igcollect/stat_per_process.cfg'):
    process_name = process_name.replace('\n','')
    cpu, mem = get_process_data(process_name)
    if cpu and mem:
        graphite_data += 'servers.' + hostname + '.software.' + process_name + '.cpu_usage ' + str(cpu) + ' ' + now + '\n'
        graphite_data += 'servers.' + hostname + '.software.' + process_name + '.mem_usage ' + str(mem) + ' ' + now + '\n'

print(graphite_data)
