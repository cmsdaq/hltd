#!/bin/env python

import sys,traceback
import os
import time
import shutil

import filecmp
import pyinotify
import threading
import Queue
import json
import logging
import hltdconf

from aUtils import *


JSDFILE = "/opt/hltd/python/def.jsd"



    #on notify, put the event file in a queue
class MonitorRanger(pyinotify.ProcessEvent):

    def __init__(self):
        super(MonitorRanger, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.eventQueue = False

    def process_default(self, event):
        self.logger.debug("event: %s on: %s" %(event.maskname,event.pathname))
        if self.eventQueue:
            self.eventQueue.put(event)

    def setEventQueue(self,queue):
        self.eventQueue = queue



class LumiSectionRanger():
    host = os.uname()[1]        
    def __init__(self,tempdir,outdir):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stoprequest = threading.Event()
        self.emptyQueue = threading.Event()    
        self.LSHandlerList = {}  # {(run,ls): LumiSectionHandler()}
        self.activeStreams = [] # updated by the ini files
        self.source = None
        self.eventtype = None
        self.infile = None
        self.EOR = None  #EORfile Object
        self.outdir = outdir
        self.tempdir = tempdir


    def join(self, stop=False, timeout=None):
        if stop: self.stop()
        super(LumiSectionRanger, self).join(timeout)

        #remove for threading
    def start(self):
        self.run()

    def stop(self):
        self.stoprequest.set()

    def setSource(self,source):
        self.source = source

    def run(self):
        self.logger.info("Start main loop") 
        while not (self.stoprequest.isSet() and self.emptyQueue.isSet() and self.checkClosure()):
            if self.source:
                try:
                    event = self.source.get(True,0.5) #blocking with timeout
                    self.eventtype = event.maskname
                    self.infile = fileHandler(event.pathname)
                    self.emptyQueue.clear()
                    self.process() 
                except (KeyboardInterrupt,Queue.Empty) as e:
                    self.emptyQueue.set() 
            else:
                time.sleep(0.5)

        self.EOR.deleteFile()
        self.logger.info("Stop main loop")


        #send the fileEvent to the proper LShandlerand remove closed LSs, or process INI and EOR files
    def process(self):
        
        filetype = self.infile.filetype
        eventtype = self.eventtype

        if eventtype == "IN_CLOSE_WRITE":
            if filetype in [STREAM,INDEX,EOLS,DAT]:
                run,ls = (self.infile.run,self.infile.ls)
                key = (run,ls)
                if key not in self.LSHandlerList:
                    self.LSHandlerList[key] = LumiSectionHandler(run,ls,self.activeStreams,self.tempdir,self.outdir)
                self.LSHandlerList[key].processFile(self.infile)
                if self.LSHandlerList[key].closed.isSet():
                    self.LSHandlerList.pop(key,None)
            elif filetype == CRASH:
                self.processCRASHfile()
            elif filetype == INI:
                self.processINIfile()
            elif filetype == EOR:
                self.processEORFile()
    
    def processCRASHfile(self):
        #send CRASHfile to every LSHandler
        lsList = self.LSHandlerList
        basename = self.infile.basename
        errCode = self.infile.data["errorCode"]
        self.logger.info("%r with errcode: %r" %(basename,errCode))
        for item in lsList.values():
            item.processFile(self.infile)

    def processINIfile(self):
            #get file information
        self.logger.info(self.infile.basename)
        infile = self.infile 

        localdir,name,ext,filepath = infile.dir,infile.name,infile.ext,infile.filepath
        run,ls,stream = infile.run,infile.ls,infile.stream

            #calc generic local ini path
        filename = "_".join([run,ls,stream,self.host])+ext
        localfilepath = os.path.join(localdir,filename)
        remotefilepath = os.path.join(self.outdir,run,filename)
            #check and move/delete ini file
        if not os.path.exists(localfilepath):
            if stream not in self.activeStreams: self.activeStreams.append(stream)
            self.infile.moveFile(newpath = localfilepath)
            self.infile.moveFile(newpath = remotefilepath,copy = True)
        else:
            self.logger.debug("compare %s , %s " %(localfilepath,filepath))
            if not filecmp.cmp(localfilepath,filepath,False):
                        # Where shall this exception be handled?
                self.logger.warning("Found a bad ini file %s" %filepath)
            else:
                self.infile.deleteFile()

    def processEORFile(self):
        self.logger.info(self.infile.basename)
        self.EOR = self.infile
        self.stop()

    def checkClosure(self):
        for key in self.LSHandlerList.keys():
            if not self.LSHandlerList[key].closed.isSet():
                return False
        return True

class LumiSectionHandler():
    host = os.uname()[1]
    def __init__(self,run,ls,activeStreams,tempdir,outdir):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(ls)

        self.activeStreams = activeStreams      
        self.ls = ls
        self.run = run
        self.outdir = outdir
        self.tempdir = tempdir    
        
        self.outfileList = []
        self.datfileList = []
        self.indexfileList = []
        self.pidList = {}           # {"pid":{"numEvents":num,"streamList":[streamA,streamB]}    
        self.EOLS = None               #EOLS file
        self.closed = threading.Event() #True if all files are closed/moved
        self.totalEvent = 0
        
        self.initOutFiles()

    def initOutFiles(self):
        activeStreams,run,ls,tempdir = self.activeStreams,self.run,self.ls,self.tempdir
        ext = ".jsn"
        if not os.path.exists(JSDFILE):
            self.logger.error("JSD file not found %r" %JSDFILE)
            return False

        for stream in self.activeStreams:
            outfilename = "_".join([run,ls,stream,self.host])+ext
            outfilepath = os.path.join(tempdir,outfilename)
            outfile = fileHandler(outfilepath)
            outfile.setJsdfile(JSDFILE)
            self.outfileList.append(outfile)


    def processFile(self,infile):
        self.infile = infile
        filetype = self.infile.filetype

        if filetype == STREAM: self.processStreamFile()
        elif filetype == INDEX: self.processIndexFile()
        elif filetype == EOLS: self.processEOLSFile()
        elif filetype == DAT: self.processDATFile()
        elif filetype == CRASH: self.processCRASHFile()

        self.checkClosure()
   

    def processStreamFile(self):
        self.logger.info(self.infile.basename)
        
        self.infile.checkSources()
        infile = self.infile
        ls,stream,pid = infile.ls,infile.stream,infile.pid
        outdir = self.outdir

        if self.closed.isSet(): self.closed.clear()
        if infile.data:
            #update pidlist
            if stream not in self.pidList[pid]["streamList"]: self.pidList[pid]["streamList"].append(stream)

            #update output files
            outfile = next((outfile for outfile in self.outfileList if outfile.stream == stream),False)
            if outfile:
                outfile.merge(infile)
                processed = outfile.getFieldByName("Processed")
                self.logger.info("ls,stream: %r,%r - events %r / %r " %(ls,stream,processed,self.totalEvent))
                infile.deleteFile()
                return True
        return False

    def processIndexFile(self):
        self.logger.info(self.infile.basename)
        infile = self.infile
        ls,pid = infile.ls,infile.pid


        if infile.data:
            numEvents = int(infile.data["data"][0])
            self.totalEvent+=numEvents
            
            #update pidlist
            if pid not in self.pidList: self.pidList[pid] = {"numEvents": 0, "streamList": []}
            self.pidList[pid]["numEvents"]+=numEvents

            if self.infile not in self.indexfileList:
                self.indexfileList.append(self.infile)
            return True
        return False

    def processCRASHFile(self):
        if self.infile.pid not in self.pidList: return True
      
        
        self.logger.info(self.infile.basename)
        infile = self.infile
        pid = infile.pid
        data  = infile.data.copy()
        numEvents = self.pidList[pid]["numEvents"]
        errCode = data["errorCode"]

        file2merge = fileHandler(infile.filepath)
        file2merge.setJsdfile(JSDFILE)
        file2merge.setFieldByName("ErrorEvents",numEvents)
        file2merge.setFieldByName("ReturnCodeMask",errCode)
        
        streamDiff = list(set(self.activeStreams)-set(self.pidList[pid]["streamList"]))
        for outfile in self.outfileList:
            if outfile.stream in streamDiff:
                outfile.merge(file2merge)

    def processDATFile(self):
        self.logger.info(self.infile.basename)
        stream = self.infile.stream
        if self.infile not in self.datfileList:
            self.datfileList.append(self.infile)

    def processEOLSFile(self):
        self.logger.info(self.infile.basename)
        ls = self.infile.ls
        if self.EOLS:
            self.logger.warning("LS %s already closed" %repr(ls))
            return False
        self.EOLS = self.infile
        #self.infile.deleteFile()   #cmsRUN create another EOLS if it will be delete too early
        return True 

    def checkClosure(self):
        if not self.EOLS: return False
        for outfile in self.outfileList:
            stream = outfile.stream
            processed = outfile.getFieldByName("Processed")+outfile.getFieldByName("ErrorEvents")
            if processed == self.totalEvent:
                self.logger.info("%r,%r complete" %(self.ls,outfile.stream))
                newfilepath = os.path.join(self.outdir,outfile.run,outfile.basename)

                    #move output file in rundir
                if outfile.moveFile(newfilepath):
                    self.outfileList.remove(outfile)
                    
                    #move all dat files in rundir
                for datfile in self.datfileList:
                    if datfile.stream == stream:
                        newfilepath = os.path.join(self.outdir,datfile.run,datfile.basename)
                        datfile.moveFile(newfilepath)
                        self.datfileList.remove(datfile)
                
            if not self.outfileList:
                #self.EOLS.deleteFile()

                #delete all index files
                for item in self.indexfileList:
                    item.deleteFile()

                #close lumisection if all streams are closed
                self.closed.set()


if __name__ == "__main__":
    logging.basicConfig(filename="/tmp/anelastic.log",
                    level=logging.INFO,
                    format='%(levelname)s:%(asctime)s-%(name)s.%(funcName)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(os.path.basename(__file__))

    #STDOUT AND ERR REDIRECTIONS
    sys.stderr = stdErrorLog()
    sys.stdout = stdOutLog()

    eventQueue = Queue.Queue()
    conf=hltdconf.hltdConf('/etc/hltd.conf')
    dirname = sys.argv[1]
    dirname = os.path.basename(os.path.normpath(dirname))
    watchDir = os.path.join(conf.watch_directory,dirname)
    outputDir = conf.micromerge_output

    mask = pyinotify.IN_CLOSE_WRITE   # watched events
    logger.info("starting anelastic for "+dirname)
    try:
        #starting inotify thread
        wm = pyinotify.WatchManager()
        mr = MonitorRanger()
        mr.setEventQueue(eventQueue)
        notifier = pyinotify.ThreadedNotifier(wm, mr)
        notifier.start()
        wdd = wm.add_watch(watchDir, mask, rec=False)


        #starting lsRanger thread
        ls = LumiSectionRanger(watchDir,outputDir)
        ls.setSource(eventQueue)
        ls.start()
    except Exception,e:
        logger.exception("error: ")
        sys.exit(1)


    logging.info("Closing notifier")
    notifier.stop()

    logging.info("Quit")
    sys.exit(0)


    

    