#!/bin/env python
from __future__ import print_function
import cgi
import time
import os
import subprocess

"""
problem: cgi scripts run as user 'nobody'
how can we handle signaling the daemon ?
"""

form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script output</TITLE>")
print("Hey I'm still here !")


#add BU suffix
bu_suffix = "_"+form["buname"].value if "buname" in form else ""

try:
    command=form['command'].value
except:
    command='herod'

command+=bu_suffix

try:os.remove(command)
except:pass
try:
    with open(command,'w+') as fp:pass
except Exception as ex:
    print("exception encountered in operating hltd (herod)\n")
    print('<P>')
    print(ex)
    raise
