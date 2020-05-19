#!/bin/env python
import cgi
import os
form = cgi.FieldStorage()
print("Content-Type: text/html")     # HTML is following
print()
print("<TITLE>CGI script output</TITLE>")
if "buname" not in form:
    print("<H1>Error</H1>")
    print("Please fill in the BU name ")
else:
    dirname = "removebox_"+form["buname"].value
    os.mkdir(dirname)
    print("<H1>"+dirname+" created</H1>")
    print("in dir "+os.getcwd())

