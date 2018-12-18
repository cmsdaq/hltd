#!/bin/env python
import cgi
import os
print("Content-Type: text/html")     # HTML is following
print()

retval=0
try:
    #listOfRuns=[x for x in [x for x in os.listdir(os.getcwd()) if True if x.startswith('run') else False]]
    listOfRuns=[ x for x in os.listdir(os.getcwd()) if x.startswith('run') ]
    for run in listOfRuns:
        retval = 1 if 'active' in os.listdir(run) else 0;
except Exception as ex:
    print(ex)
print(retval);
