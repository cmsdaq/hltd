#!/bin/env python
from __future__ import print_function
import cgi
import os
RUNNUMBER_PADDING=6
form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script output</TITLE>")
if "run" not in form:
    print("<H1>Error</H1>")
    print("Please fill in the run number ")
else:
    #add BU suffix
    bu_suffix = "_"+form["buname"].value if "buname" in form else ""
    os.mkdir('run'+str(form["run"].value).zfill(RUNNUMBER_PADDING)+bu_suffix)
    print("<H1>run "+str(form["run"].value)+" created</H1>")
    print("in dir "+os.getcwd())
