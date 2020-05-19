#!/bin/env python
from __future__ import print_function

import os
import sys
import SOAPpy
try:
  import setproctitle
except:
  pass
sys.path.append('/opt/hltd/python')
#sys.path.append('/opt/hltd/lib')
import demote
import hltdconf

def writeToFile(filename,content,overwrite):
    try:
        os.stat(filename)
        #file exists
        if overwrite=="False":return
    except:
        pass
    try:
        with open(filename,'w') as file:
            file.write(content)
        return "Success"
    except IOError as ex:
        return "Failed to write data: "+str(ex)

def createDirectory(dirname):
    try:
        os.mkdir(dirname)
        return "Success"
    except OSError as ex:
        return "Failed to create directory: "+str(ex)

def renamePath(oldpath,newpath):
    try:
        os.rename(oldpath,newpath)
        return "Success"
    except Exception as ex:
        return  "Failed to rename file: "+str(ex)

class Soap2file:

    def __init__(self):
        self._conf=hltdconf.hltdConf('/etc/hltd.conf')
        self._hostname = os.uname()[1]

    def checkEnabled(self):
        if self._conf.soap2file_port>0:return True
        return False

    def run(self):
        dem = demote.demote(self._conf.user)
        dem()

        server = SOAPpy.SOAPServer((self._hostname, self._conf.soap2file_port))
        server.registerFunction(writeToFile)
        server.registerFunction(createDirectory)
        server.registerFunction(renamePath)
        server.serve_forever()

if __name__ == "__main__":

    daemon = Soap2file()
    try:
      setproctitle.setproctitle('soap2file')
    except:
      pass
    #NOTE:forking mode is unused and obsolete

    if daemon.checkEnabled():
        daemon.run()
    else:
        print("Soap2file service is disabled")
        sys.exit(0)

