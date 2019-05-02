#!/bin/env python
from __future__ import print_function
import cgi
import time
import os
import subprocess

print("Content-Type: text/html")     # HTML is following
print()
try:os.remove('restart')
except:pass
try:
    with open('restart','w+') as fp: pass
except Exception as ex:
    print("exception encountered in operating hltd\n")
    print('<P>')
    print(ex)
    raise

print("Rebirth planning commenced.")
