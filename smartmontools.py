#!/usr/bin/env python
#
# igcollect - smartmontools
#
# Copyright (c) 2016, InnoGames GmbH
#

import glob
import time
import socket


def main():
    for filename in glob.glob('/var/lib/smartmontools/*.state'):
        template = (
            'servers.{0}.hardware.smart.{1}.{{0}}.{{1}} {{2}} {2}'.format(
                socket.gethostname().replace('.', '_'),
                filename.split('.', 2)[1],
                int(time.time()),
            )
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
