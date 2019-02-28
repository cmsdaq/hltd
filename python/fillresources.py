#!/bin/env python

import os
import shutil
import hltdconf
import time
import sys


def clearDir(dir):
    try:
        files = os.listdir(dir)
        for file in files:
            try:
                os.unlink(os.path.join(dir,file))
            except:
                pass
    except:
        pass

def updateIdles(idledir,newcount):
    current = len(os.listdir(idledir))
    if newcount==current:
      #already updated
      return 0
    if newcount>current:
      totAdd=toAdd
      toAdd = newcount-current
      index=0
      while toAdd:
        if not os.path.exists(idledir+'/idle/core'+str(index)):
          open(conf.resource_base+'/idle/core'+str(index),'a').close()
          toAdd-=1
        index+=1
      return totAdd
    if newcount<current:
      def cmpf(x,y):
        if int(x[4:])<int(y[4:]): return 1
        elif int(x[4:])>int(y[4:]): return -1
        else:return 0
      invslist = sorted(os.listdir(idledir),cmp=cmpf)
      toDelete = newcount-current
      totDel=toDelete
      for i in invslist:
          os.unlink(os.path.join(idledir,i))
          toDelete-=1
          if toDelete==0:break
          return -totDel


resource_count = 0

def runFillResources(force):

    conf=hltdconf.hltdConf('/etc/hltd.conf')

    #NOTE:will not work with daq3val, role must be set
    if conf.role==None and (os.uname()[1].startswith('fu-') or os.uname()[1].startswith('dvrubu-') or os.uname()[1].startswith("d3vfu-")): role='fu'
    else: role = conf.role

    if role=='fu' and not conf.dqm_machine:

        #no action on FU if using dynamic resource setting (default)
        if not conf.dynamic_resources or force:

            clearDir(conf.resource_base+'/idle')
            clearDir(conf.resource_base+'/online')
            clearDir(conf.resource_base+'/except')
            clearDir(conf.resource_base+'/quarantined')

            #if any resources found in cloud, machine assumed to be running cloud
            foundInCloud=len(os.listdir(conf.resource_base+'/cloud'))>0
            clearDir(conf.resource_base+'/cloud')

            def fillCores():
                global resource_count
                with open('/proc/cpuinfo','r') as fp:
                    for line in fp:
                        if line.startswith('processor'):
                            #by default do not touch cloud settings,unless force
                            if foundInCloud and not force:
                                open(conf.resource_base+'/cloud/core'+str(resource_count),'a').close()
                            else:
                                open(conf.resource_base+'/quarantined/core'+str(resource_count),'a').close()
                            resource_count+=1

            fillCores()
            #fill with more cores for VM environment
            if os.uname()[1].startswith('fu-vm-'):
                fillCores()
                fillCores()
                fillCores()

if __name__ == "__main__":

    force_param=False
    if len(sys.argv)>1 and sys.argv[1]=='force':
        force_param=True
    runFillResources(force_param)
