#!/usr/bin/env python
"""igcollect - S.M.A.R.T.

Copyright (c) 2017 InnoGames GmbH
"""

from argparse import ArgumentParser
from glob import glob
from time import time


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='smart')
    return parser.parse_args()


def main():
    args = parse_args()
    for filename in glob('/var/lib/smartmontools/*.state'):
        template = (
            '{0}.{1}.{{0}}.{{1}} {{2}} {2}'
            .format(args.prefix, filename.split('.', 2)[1], int(time()))
        )

        with open(filename, 'r') as fd:
            metric_id = None

            for line in fd.readlines():
                if line.startswith('ata-smart-attribute'):
                    desc, value = line.split('=', 1)
                    value_type = desc.split('.', 2)[2].strip()
                    value = value.strip()

                    if value_type == 'id':
                        metric_id = value
                        continue

                    print(template.format(metric_id, value_type, value))


if __name__ == '__main__':
    main()
