#!/bin/env python
import cgi
import os
from __future__ import print_function
print("Content-Type: text/html")     # HTML is following
print()                               # blank line, end of headers
#print([x[3:] for x in [x for x in os.listdir(os.getcwd()) if True if x.startswith('run') else False]])
print([ x[3:] for x in os.listdir(os.getcwd()) if x.startswith('run') ])
