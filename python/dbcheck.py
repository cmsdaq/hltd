#!/bin/env python
from __future__ import print_function

import os,sys
import json

from setupmachine import getBUAddr
dbhost__='null'

#dblogin__='CMS_DAQ2_HW_CONF_R'
#dbsid__='cms_rcms'
#dbpwd__='password'
#tag__='daq2'

with open('/opt/fff/db.jsn','r') as fi:
    cred = json.load(fi)

dbsid__=cred['sid']
dblogin__=cred['login']
dbpwd__=cred['password']

host__=os.uname()[1]+'.cms'
if host__.startswith('dv'):
    tag__='daq2val'
else:
    tag__='daq2'

env__='prod'
eqset__='latest'
try:eqset__=sys.argv[4]
except:pass
problem_found=False
addr_arr = []
addrlist =  getBUAddr(tag__,host__,env__,eqset__,dbhost__,dblogin__,dbpwd__,dbsid__)
for addr in addrlist:
    print("Found remote address",addr)
    ret = os.system("ping -c 1 "+addr[1]+ ' > /dev/null')
    if not ret:
        print("Ping test successful",addr[1])
    else:
        print("Ping test FAILED, exit code:",ret)
        problem_found=True
    addr_arr.append(addr[1])


with open('/etc/appliance/bus.config','r') as fi:
    flist1=  fi.readlines()
    flist=[]
    for f in flist1: flist.append(f.strip('\n'))
    if sorted(flist) != sorted(addr_arr):
        print("Inconsistent bus.config. Try rerunning /opt/fff/configurefff.sh on this machine")
        problem_found=True

sys.exit(problem_found)
