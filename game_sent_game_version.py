#!/usr/bin/env python
#
# igcollect - Sent currently deployed game version.
#
# Copyright (c) 2016 InnoGames GmbH
#

import os
import re
import socket

# All possible revision files for all games.
revision_file = [
    '/www/ds/revision',
    '/www/grepo/branch',
    '/www/foe/version',
    '/www/onyx/branch',
]

if __name__ == '__main__':
    # Game name can be found from hostname, I think.
    hostname = socket.gethostname()

    # Hostname suffix should be the shortcode.
    game_shortcode = hostname.split('.')[-1]

    # Game market should be first two characters of hostname.
    game_market = hostname[:2]

    # World name should be first characters followed by numbers.
    regex = re.search('^[a-z]+[0-9]+', hostname)
    game_worldname = regex.group(0)

    # If all goes well, this variable will be set to revision.
    revision = None

    for filename in revision_file:
        if os.path.exists(filename):
            with open(filename, 'r') as fh:
                revision = fh.readlines()[0]

                # For Tribalwars the version starts after the first space
                if filename.startswith('/www/ds'):
                    revision = revision.split(' ')[-1]

                # For Elvenar stip the 'v' from the beginning.
                if filename.startswith('/www/onyx'):
                    if revision.startswith('v'):
                        revision = revision[1:]

    if revision:
        # Replace all the dots.
        revision = revision.replace('.', '_')

        # Print data if revision was valid.
        print 'games.{}.{}.{}.version.{}'.format(
            game_shortcode, game_market, game_worldname, revision)

