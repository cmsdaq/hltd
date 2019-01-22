#!/bin/env python
import cgi
import os
from __future__ import print_function
form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script suspend</TITLE>")

portsuffix=""
if "port" in form:
    portsuffix=form["port"].value

try:
    os.unlink('suspend'+portsuffix)
except:
    pass
fp = open('suspend'+portsuffix,'w+')
fp.close()
