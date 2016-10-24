#!/usr/bin/env python
#
# igcollect - Sent currently deployed game version.
#
# Copyright (c) 2016 InnoGames GmbH
#

import os
import time

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='game.ds.xx.xx1.version')
    parser.add_argument('--filename', default='/www/ds/revision')

    return vars(parser.parse_args())

def main(prefix, path):
    # If all goes well, this variable will be set to revision.
    revision = None

    if os.path.exists(filename):
        with open(filename, 'r') as fh:
            revision = fh.readlines()[0]

            # If revision contains spaces, take last element.
            if ' ' in revision:
                revision = revision.split(' ')[-1]

            # Strip leading 'v' from version string
            if revision.startswith('v'):
                revision = revision[1:]

            # Replace all the dots.
            revision = revision.replace('.', '_')

    if revision:
        # Print data if revision was valid.
        print('{}.{} 1 {}'.format(prefix, revision, int(time.time())))

if __name__ == '__main__':
    main(**parse_args())

