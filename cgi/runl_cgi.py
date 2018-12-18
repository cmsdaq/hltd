#!/usr/bin/env python2
import cgi
import os
print("Content-Type: text/html")     # HTML is following
print()                               # blank line, end of headers
print([x[3:] for x in [x for x in os.listdir(os.getcwd()) if True if x.startswith('run') else False]])
