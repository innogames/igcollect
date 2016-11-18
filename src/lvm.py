#!/usr/bin/env python
#
# igcollect - Linux volume manager
#
# Copyright (c) 2016, InnoGames GmbH
#

from argparse import ArgumentParser
from subprocess import check_output
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='lvm')
    return parser.parse_args()


def main():
    args = parse_args()
    vgdisplay = check_output(('/sbin/vgdisplay', '-c'))
    template = args.prefix + '.{}.{} {} ' + str(int(time()))

    for line in vgdisplay.splitlines():
        # 1     2 3 4 5 6 7 8 9 0 1 12      13      4 5 16      7
        line_split = line.strip().split(':')
        assert len(line_split) == 17
        vg_name = line_split[0]
        vg_size = line_split[11]
        pe_size = line_split[12]
        free_pe = line_split[15]
        vg_size_gib = float(vg_size) / 1024.0 / 1024.0
        vg_free_gib = float(pe_size) * float(free_pe) / 1024.0 / 1024.0
        print(template.format(vg_name, 'size_gib', vg_size_gib))
        print(template.format(vg_name, 'free_gib', vg_free_gib))
        print(template.format(vg_name, 'free_pe', free_pe))


if __name__ == '__main__':
    main()
