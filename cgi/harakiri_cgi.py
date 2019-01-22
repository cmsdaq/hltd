#!/bin/env python
import cgi
import time
import os
import subprocess
from __future__ import print_function

"""
problem: cgi scripts run as user 'nobody'
how can we handle signaling the daemon ?
"""

form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script output</TITLE>")
print("Hey I'm still here !")

try:
    if os.path.exists('harakiri'):
        os.remove('harakiri')
    fp = open('harakiri','w+')
    fp.close()
except Exception as ex:
    print("exception encountered in operating hltd\n")
    print('<P>')
    print(ex)
    raise
