#!/bin/env python
import os
import time
import sys

sys.path.append('/opt/hltd/python')
import hltdconf


def clearDir(dirname):
    try:
        files = os.listdir(dirname)
        for filename in files:
            try:
                os.unlink(os.path.join(dirname,filename))
            except:
                pass
    except:
        pass

resource_count = 0

def runFillResources(force):

    conf=hltdconf.hltdConf('/etc/hltd.conf')

    if conf.role in [None,"None"] and (os.uname()[1].startswith('fu-') or os.uname()[1].startswith('dvrubu-') or os.uname()[1].startswith("d3vfu-")):
        role='fu'
    else:
        role = conf.role

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

if __name__ == "__main__":

    force_param=False
    if len(sys.argv)>1 and sys.argv[1]=='force':
        force_param=True
    runFillResources(force_param)
