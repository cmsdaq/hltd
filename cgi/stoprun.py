#!/bin/env python
from __future__ import print_function
import cgi
form = cgi.FieldStorage()
if "run" not in form:
    print("<H1>Error</H1>")
    print("Please fill in the run number ")
else:
    try: os.remove('end'+form["run"].value)
    except:pass
    with open('end'+form["run"].value) as fp: pass
