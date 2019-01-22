#!/bin/env python
import cgi
import os
from __future__ import print_function
form = cgi.FieldStorage()

boxesdir='appliance/boxes/'

print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script suspend</TITLE>")
if "host" not in form:
    print("<H1>Error</H1>")
    print("Please provide host name ")
else:
    os.unlink(boxesdir+str(form["host"].value))
    print("<H1>file "+os.getcwd()+boxesdir+str(form["host"].value)+" deleted</H1>")
