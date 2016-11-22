#!/usr/bin/env python
#
# igcollect - process stat
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from subprocess import check_output
import os.path
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='processes')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{}.{} {} ' + str(int(time()))
    for process_name in get_process_list('/etc/igcollect/stat_per_process.cfg'):
        process_name = process_name.replace('\n', '')
        cpu, mem = get_process_data(process_name)
        print(template.format(process_name, 'cpu_usage', cpu))
        print(template.format(process_name, 'mem_usage', mem))


def get_process_list(config_file):
    content = ''
    if os.path.isfile(config_file):
        with open(config_file) as f:
            content = f.readlines()
    return content


def get_process_data(process_name):
    pid = check_output(['pgrep', '-f', process_name]).strip()
    process_data = check_output(('ps', '-p', pid, '-o', 'pcpu=,pmem=')).strip()
    return process_data.split()


if __name__ == '__main__':
    main()
