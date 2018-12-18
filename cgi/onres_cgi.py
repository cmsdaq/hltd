#!/usr/bin/env python
import cgi
import os
print("Content-Type: text/html")     # HTML is following
print()                               # blank line, end of headers
print(os.listdir(os.getcwd()+'/resources/online'))
