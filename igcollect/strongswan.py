#!/usr/bin/env python
"""igcollect - Strongswan stats

Copyright (c) 2020 InnoGames GmbH
"""

import binascii
import re
import vici

from argparse import ArgumentParser
from hashlib import pbkdf2_hmac
from time import time

# Keep metric names consistent with what we have on other systems which probably
# comes from SNMP. Translate from metrics used by Strongswan.
METRICS = {
    'bytesIn': 'bytes-in',
    'bytesOut': 'bytes-out',
    'pktsIn': 'packets-in',
    'pktsOut': 'packets-out',
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--prefix', help='Graphite path prefix', default='strongswan',
    )
    parser.add_argument(
        '--salt', help="Hash client names using this salt when it's specified",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Get all connections and materialize enumerator into a list for later use.
    sas = list(vici.Session().list_sas())

    template = args.prefix + '.{} {} ' + str(int(time()))
    print(template.format('clients', len(sas)))

    for client_name, client_data in get_clients_traffic(sas).items():
        # For privacy we support hashing client login name.
        if args.salt:
            client_hash = binascii.hexlify(
                pbkdf2_hmac(
                    'sha256', client_name.encode(), args.salt.encode(), 100
                )
            ).decode()
        else:
            client_hash = client_name
        for metric in METRICS:
            print(template.format('clients_traffic.{}.{}'.format(
                client_hash, metric), client_data[metric]
            ))


def get_clients_traffic(sas):
    ret = {}
    for sa in sas:
        for connection in sa.values():
            # Get username of connected client. 
            user = connection.get('remote-eap-id')
            # Linux users are connected without "remote-eap-id".
            if not user:
                user = connection.get('remote-id')
            # Let's not crash the whole script if one user can't be identified.
            if not user:
                continue
            user = user.decode()
            # Strip AD domain name.
            user = re.sub(r'[A-Z\\]', '', user)
            # Convert to a valid Graphite metric name.
            user = user.replace('.', '_')
            for child_sa in connection['child-sas'].values():
                if user not in ret:
                    ret[user] = {x:0 for x in METRICS}

                # That's Graphite metric and Strongswan metric
                for gm, sm in METRICS.items():
                    ret[user][gm] += int(child_sa[sm].decode())
    return ret

if __name__ == '__main__':
    main()
