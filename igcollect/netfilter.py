#!/usr/bin/env python
"""igcollect - Linux packet filter

Copyright (c) 2023 InnoGames GmbH
"""


from argparse import ArgumentParser
from nftables import Nftables
from nftables import json
from subprocess import check_output
from time import time

NF_OIDS = [
    'nf_conntrack_count',
    'nf_conntrack_max',
]


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='software.netfilter')
    parser.add_argument('--snat', nargs='+')
    return parser.parse_args()


def main():
    args = parse_args()

    template = args.prefix + '.{} {} ' + str(int(time()))

    for name, value in get_nf_info().items():
        print(template.format(name, value))

    if args.snat:
        for name, value in get_snat_info(args.snat).items():
            print(template.format(name, value))

    for name, value in get_counters_info().items():
        print(template.format(name, value))


def get_nf_info():
    ret = {}
    for oid in NF_OIDS:
        with open(f'/proc/sys/net/netfilter/{oid}', 'r') as f:
            for l in f.readlines():
                # There should be just one line
                value = int(l)
        ret[f'sysctl.{oid}'] = value
    return ret


def get_snat_info(snats):
    ret = {}
    for snat in snats:
        snat_states=len(check_output(
            ['/sbin/conntrack', '-L', '-n', '-q', snat],
        ).decode().splitlines())
        snat_safe = snat.replace('.', '_').replace(':', '_')
        ret[f'snat.{snat_safe}'] = snat_states
    return ret


def get_counters_info():
    ret = {}
    nft = Nftables()
    nft.set_json_output(True)
    _, nft_output, _ = nft.cmd(f"list counters")

    for data in json.loads(nft_output)['nftables']:
        counter = data.get('counter')
        if not counter:
            continue
        safe_name = counter['name'].replace('.', '_').replace(':', '_')
        ret[f'counters.{safe_name}.packets'] = counter['packets']
        ret[f'counters.{safe_name}.bytes'] = counter['bytes']
    return ret


if __name__ == '__main__':
    main()
