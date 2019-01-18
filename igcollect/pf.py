#!/usr/bin/env python
"""igcollect - FreeBSD Packet Filter

Copyright (c) 2016 InnoGames GmbH
"""

from __future__ import print_function
from argparse import ArgumentParser
from subprocess import check_output
from time import time
import re

# pfctl displays stats in a tree-like structure.
# There is no single like that could denote given counter.
#
# ----- 8< -----
# State Table                          Total             Rate
#   current entries                   112553
# ...
# Source Tracking Table
#   current entries                    21032
# ----- >8 -----
#
# Because of that we must split the output into sections and sub-sections.

PF_INFOS = {
    'states': ('State Table', 'current entries'),
    'state_insert': ('State Table', 'inserts'),
    'state_search': ('State Table', 'searches'),
    'state_removal': ('State Table', 'removals'),
    'src_nodes': ('Source Tracking Table', 'current entries'),
    'src_node_insert': ('Source Tracking Table', 'inserts'),
    'src_node_search': ('Source Tracking Table', 'searches'),
    'src_node_removal': ('Source Tracking Table', 'removals'),
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='software.pf')
    return parser.parse_args()


def parse_pf_info():

    pf_info_raw = check_output(
            ['/sbin/pfctl', '-qvsi'],
            universal_newlines=True,
            close_fds=False,
    ).splitlines()

    pf_info = {}
    for pf_info_graphite, (pf_info_section, pf_info_key) in PF_INFOS.items():
        key_re = re.compile('\s+{}'.format(pf_info_key))
        in_section = False
        for line in pf_info_raw:
            if line.startswith(pf_info_section):
                in_section = True
            if in_section and key_re.match(line):
                val = key_re.split(line)
                pf_info[pf_info_graphite] = val[1].split()[0]
                break
    return pf_info


def main():
    args = parse_args()

    template = args.prefix + '.{} {} ' + str(int(time()))

    for graphite_var, pf_val in parse_pf_info().items():
        print(template.format(graphite_var, pf_val))


if __name__ == '__main__':
    main()
