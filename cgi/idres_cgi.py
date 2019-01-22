#!/bin/env python
import cgi
import os
from __future__ import print_function
print("Content-Type: text/html")     # HTML is following
print()                               # blank line, end of headers
print(os.listdir(os.getcwd()+'/resources/idle'))
