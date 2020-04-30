#!/usr/bin/env python
"""igcollect - Strongswan stats

Copyright (c) 2020 InnoGames GmbH
"""

from argparse import ArgumentParser
from subprocess import check_output
from time import time
import re


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='strongswan')
    return parser.parse_args()


def main():
    args = parse_args()
    template = args.prefix + '.{} {} ' + str(int(time()))
    print(template.format('clients', count_connected_clients()))


def count_connected_clients():
    # Single connected users looks like this:

    # ---- 8< ----
    # vpn_by_id_group_xyz: #974, ESTABLISHED, IKEv2, 4242424242424242_i 4242424242424242_r*
    #   local  'XXXXXX.example.com' @ XXX.XXX.XXX.XXX[4500]
    #   remote 'XXX.XXX.XXX.XXX' @ XXX.XXX.XXX.XXX[56128] EAP: 'user.name' [XXX.XXX.XXX.XXX XXX:XXX:XXX::XXX]
    #   AES_CBC-256/HMAC_SHA1_96/PRF_HMAC_SHA1/MODP_1024
    #   established 6648s ago, rekeying in 6393s
    #   vpn_by_id_group_xyz: #2624, reqid 426, INSTALLED, TUNNEL-in-UDP, ESP:AES_CBC-256/HMAC_SHA1_96
    #     installed 3354s ago, rekeying in 53s, expires in 606s
    #     in  42424242 (-|0x000675ec), 9577036 bytes, 63405 packets,     2s ago
    #     out 42424242 (-|0x000675ec), 20466058 bytes, 68523 packets,     2s ago
    #     local  0.0.0.0/0 ::/0
    #     remote XXX.XXX.XXX.XXX/32 XXX:XXX:XXX::XXX/128
    # ---- >8 ----

    # Let's say that the line containing word 'remote' and IP address of the client
    # identifies a single client.
    line_re = re.compile(r'^\s+remote .* @')

    output = check_output(['/usr/sbin/swanctl', '--list-sas']).decode()
    lines = output.splitlines()
    return sum(1 for l in lines if line_re.match(l))

if __name__ == '__main__':
    main()
