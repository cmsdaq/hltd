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
    #check for duplicate:
    run_short = 'run'+str(form["run"].value).zfill(RUNNUMBER_PADDING)
    run_long = 'run'+str(form["run"].value).zfill(RUNNUMBER_PADDING)+bu_suffix
    #check for both variants (renaming race)
    if os.path.exists(run_long) or os.path.exists(run_short):
        print("<H1>run "+str(form["run"].value)+" alreary exists</H1>")
        print("in dir "+os.getcwd())
        #trip exception 
        raise FileExistsError("Directory for " + run_short + " exists")
    else:
        os.mkdir(run_short+bu_suffix)
        print("<H1>run "+str(form["run"].value)+" created</H1>")
        print("in dir "+os.getcwd())
