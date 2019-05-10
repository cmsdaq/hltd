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

try:os.remove('suspend'+portsuffix)
except: pass

with open('suspend'+portsuffix,'w+') as fp: pass
