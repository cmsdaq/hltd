#!/bin/env python
from __future__ import print_function
import cgi
import os
form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script exclude</TITLE>")

try:
    os.unlink('exclude')
except:
    pass
fp = open('exclude','w+')
fp.close()
