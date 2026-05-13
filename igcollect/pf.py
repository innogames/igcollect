#!/usr/bin/env python3
"""igcollect - FreeBSD Packet Filter

Copyright © 2026 InnoGames GmbH
"""

import re
import sysctl
from argparse import ArgumentParser
from subprocess import check_output
from time import time

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
    'drop_bad_offset': ('Counters', 'bad-offset'),
    'drop_bad_timestamp': ('Counters', 'bad-timestamp'),
    'drop_congestion': ('Counters', 'congestion'),
    'drop_fragment': ('Counters', 'fragment'),
    'drop_ip_option': ('Counters', 'ip-option'),
    'drop_map_failed': ('Counters', 'map-failed'),
    'drop_memory': ('Counters', 'memory'),
    'drop_normalize': ('Counters', 'normalize'),
    'drop_proto_checksum': ('Counters', 'proto-cksum'),
    'drop_short': ('Counters', 'short'),
    'drop_src_limit': ('Counters', 'src-limit'),
    'drop_state_insert': ('Counters', 'state-insert'),
    'drop_state_limit': ('Counters', 'state-limit'),
    'drop_state_mismatch': ('Counters', 'state-mismatch'),
    'drop_synproxy': ('Counters', 'synproxy'),
    'drop_translate': ('Counters', 'translate'),
    'src_node_insert': ('Source Tracking Table', 'inserts'),
    'src_node_removal': ('Source Tracking Table', 'removals'),
    'src_node_search': ('Source Tracking Table', 'searches'),
    'src_nodes': ('Source Tracking Table', 'current entries'),
    'state_insert': ('State Table', 'inserts'),
    'state_removal': ('State Table', 'removals'),
    'state_search': ('State Table', 'searches'),
    'states': ('State Table', 'current entries'),
}

UMA_INFOS = (
    'pf_Ethernet_anchors',
    'pf_UDP_mappings',
    'pf_anchors',
    'pf_frag_entries',
    'pf_fragment_node',
    'pf_frags',
    'pf_mtags',
    'pf_source_nodes',
    'pf_state_keys',
    'pf_state_scrubs',
    'pf_states',
    'pf_table_entries',
    'pf_table_entry_counters',
    'pf_tags',
)


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


def parse_pf_memory_info():
    pf_info = {}
    for uma_info in UMA_INFOS:
        ctl = sysctl.filter(f'vm.uma.{uma_info}.stats.current')
        if ctl:
            value = sysctl.filter(f'vm.uma.{uma_info}.stats.current')[0].value
            pf_info[uma_info] = value
    return pf_info


def main():
    args = parse_args()

    template = args.prefix + '.{} {} ' + str(int(time()))

    for graphite_var, pf_val in (
            parse_pf_info().items() |
            parse_pf_memory_info().items()
    ):
        print(template.format(graphite_var, pf_val))


if __name__ == '__main__':
    main()
