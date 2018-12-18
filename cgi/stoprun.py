#!/usr/bin/env python
import cgi
form = cgi.FieldStorage()
if "run" not in form:
    print("<H1>Error</H1>")
    print("Please fill in the run number ")
else:
    fp = open('end'+form["run"].value)
    fp.close()
