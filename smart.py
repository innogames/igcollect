#!/usr/bin/env python
#
# igcollect - S.M.A.R.T.
#
# Copyright (c) 2016, InnoGames GmbH
#

from __future__ import print_function
from socket import gethostname
import glob, time, sys

try:
    STATE_FILES=glob.glob('/var/lib/smartmontools/*.state')
except:
    sys.exit(1)

graphite=''
now=str(int(time.time()))
hostname=gethostname()

for file in STATE_FILES:
    try:
        f = open (file,'r')
        data = f.readlines()
        f.close()
    except:
        sys.exit(1)

    a,diskid,a=file.split('.',2)

    id='aaa'
    for line in data:
        if line.startswith('ata-smart-attribute'):
            desc,value = line.split('=',1)
            a,a,valtype=desc.strip().split('.',2)
            if valtype == 'id':
               id = value.strip()
            else:
               graphite += 'servers.%s.hardware.smart.%s.%s.%s %s %s\n' % (hostname.replace('.','_'),diskid,str(id),valtype,str(value.strip()),now)

print(graphite)
