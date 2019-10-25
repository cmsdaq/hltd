#!/bin/env python
from __future__ import print_function
import cgi
import os
form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script suspend</TITLE>")

portsuffix=""
if "port" in form:
    portsuffix=form["port"].value

def mkfile(filename):
    try:os.remove(filename)
    except: pass
    with open(filename,'w+') as fp:
      pass

if str(portsuffx)!="" and str(portsuffix)!="0":
    try:
        ipaddress = cgi.escape(os.environ["REMOTE_ADDR"])
        mkfile('suspend')+portsuffix+'_'+ipaddress
    except:
        mkfile('suspend'+portsuffix)
else:
    mkfile('suspend'+portsuffix)
