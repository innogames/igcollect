#!/usr/bin/env python
#
# igcollect - Memcached
#
# Copyright (c) 2016, InnoGames GmbH
#

import re, telnetlib, sys, socket, time

class MemcachedStats:

    _client = None
    _key_regex = re.compile(ur'ITEM (.*) \[(.*); (.*)\]')
    _slab_regex = re.compile(ur'STAT items:(.*):number')
    _stat_regex = re.compile(ur"STAT (.*) (.*)\r")

    def __init__(self, host='localhost', port='11211'):
        self._host = host
        self._port = port

    @property
    def client(self):
        if self._client is None:
            self._client = telnetlib.Telnet(self._host, self._port)
        return self._client

    def command(self, cmd):
        ' Write a command to telnet and return the response '
        self.client.write("%s\n" % cmd)
        return self.client.read_until('END')

    def stats(self):
        ' Return a dict containing memcached stats '
        return dict(self._stat_regex.findall(self.command('stats')))

def main(argv=None):
    if not argv:
        argv = sys.argv
    host = argv[1] if len(argv) >= 2 else '127.0.0.1'
    port = argv[2] if len(argv) >= 3 else '11211'
    m = MemcachedStats(host, port)
    memcached = {}
    memcached=m.stats()
    hostname = socket.gethostname().replace('.', '_')
    timestamp = str(int(time.time()))
    template = 'servers.' + hostname + '.software.memcached.{1} {2} ' + timestamp

    for key in memcached:
      try:
        float(memcached[key])
        print(template.format(hostname,key, memcached[key]))
      except ValueError:
        pass


if __name__ == '__main__':
    main()
