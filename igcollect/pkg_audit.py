#!/usr/bin/env python3
"""igcollect - audit installed packages against known vulnerabilities

Copyright (c) 2023 InnoGames GmbH
"""

from __future__ import print_function
from argparse import ArgumentParser
from subprocess import check_output
from time import time

# Translate netstat columns to what we store in Graphite
# Output of netstat looks like this:
#
# ----- 8< -----
# Name    Mtu Network       Address              Ipkts Ierrs Idrop     Ibytes    Opkts Oerrs     Obytes  Coll  Drop
# inter  1500 <Link#7>      a0:36:9f:9c:f5:c4 25125485     0     0 19227525718  9004705    49 17356471801     0     0
# inter     - fe80::a236:9f fe80::a236:9fff:f       24     -     -       1600       10     -        752     -     -
# inter     - 10.193.0.0/16 10.193.240.3       8475696     -     -  929957904 16355963     - 17197654383     -     -
# inter     - 2a00:1f78:fff 2a00:1f78:fffd:40  1089342     -     -   90052809   347269     -   32679155     -     -
# ----- >8 -----
#
# 0      1    2             3                  4           5     6     7         8     9         10       11   12

NETSTAT_COLUMNS = {
    'pktsIn': 4,
    'errorsIn': 5,
    'dropsIn': 6,
    'bytesIn': 7,
    'pktsOut': 8,
    'errorsOut': 9,
    'bytesOut': 10,
}


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='network')
    return parser.parse_args()


def parse_netstat():
    iface_info={}

    ifaces = check_output(
        ['/sbin/ifconfig', '-l'],
        universal_newlines=True,
        close_fds=False,
    ).split()

    for iface in ifaces:
        iface_info[iface] = {}
        # 0th line is header, 1st line is link information,
        # follwing lines are stats per subnet on interface
        netstat = check_output(
            ['/usr/bin/netstat', '-I', iface, '-nbd'],
            universal_newlines=True,
            close_fds=False,
        ).splitlines()[1].split()

        for column, index in NETSTAT_COLUMNS.items():
            if len(netstat) == 12:
                # Tunnel interfaces have no MAC
                index -= 1
            iface_info[iface][column] = netstat[index]

    return iface_info


def main():
    args = parse_args()

    template = args.prefix + '.{}.{} {} ' + str(int(time()))

    for iface, iface_info in parse_netstat().items():
        for name, value in iface_info.items():
            print(template.format(iface, name, value))


if __name__ == '__main__':
    main()
