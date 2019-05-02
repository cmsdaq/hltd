#!/bin/env python
from __future__ import print_function
import cgi
import os
form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script output</TITLE>")
if "run" not in form:
    print("<H1>Error</H1>")
    print("Please fill in the run number ")
else:
    try:os.remove('end'+str(form["run"].value))
    except:pass

    with open('end'+str(form["run"].value),'w+') as fp:pass
    print("<H1>run "+str(form["run"].value)+" stopped</H1>")
    print("in dir "+os.getcwd())
