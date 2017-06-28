#!/usr/bin/env python
#
# igcollect - Directory size stat
#
# Copyright (c) 2017, InnoGames GmbH
#

import os
from argparse import ArgumentParser
from time import time


def main():
    args = parse_args()
    template = '{}.{{}} {{}} {}'.format(args.prefix, int(time()))

    for directory in args.directories:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        print(template.format(directory.replace('/', '', 1).replace('/', '_'), total_size))



def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='directory')
    parser.add_argument('--directories', default=[], nargs='+', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    main()
