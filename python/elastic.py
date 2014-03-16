#!/bin/env python

import sys,traceback
import os

import logging
import _inotify as inotify
import threading
import Queue

import elasticBand
import hltdconf

from anelastic import *



class BadIniFile(Exception):
    pass


class elasticCollector(LumiSectionRanger):
    
    def __init__(self, esDir):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.esDirName = esDir
    
    def process(self):
        self.logger.debug("RECEIVED FILE: %s " %(self.infile.basename))
        filepath = self.infile.filepath
        fileType = self.infile.fileType
        eventType = self.eventType
        if eventType & inotify.IN_CLOSE_WRITE:
            if self.esDirName in self.infile.dir:
                if fileType in [INDEX,STREAM,OUTPUT]:   self.elasticize(filepath,fileType)
                if fileType in [EOR]: self.stop()
                self.infile.deleteFile()
            elif fileType in [FAST,SLOW]:
                return
        #DEBUG
        if eventType & inotify.IN_DELETE:
            self.logger.info("file " + filepath + " deleted")

        if eventType & inotify.IN_CREATE:
            self.logger.info("file " + filepath + " created")

        if eventType & inotify.IN_MODIFY:
            self.logger.info("file " + filepath + " modified")

        if eventType & inotify.IN_MOVED_TO:
            self.logger.info("file " + filepath + " moved")

        if eventType & inotify.IN_CLOSE_WRITE:
            self.logger.info("file " + filepath + " closed")



                #self.elasticize(filepath,fileType)


    def elasticize(self,filepath,fileType):
        self.logger.debug(filepath)
        path = os.path.dirname(filepath)
        name = os.path.basename(filepath)
        if es and os.path.isfile(filepath):
            if fileType == FAST: es.elasticize_prc_istate(path,name)
            elif fileType == SLOW: es.elasticize_prc_sstate(path,name)             
            elif fileType == INDEX: 
                self.logger.info(name+" going into prc-in")
                es.elasticize_prc_in(path,name)
            elif fileType == STREAM:
                self.logger.info(name+" going into prc-out")
                es.elasticize_prc_out(path,name)
            elif fileType == OUTPUT:
                self.logger.info(name+" going into fu-out")
                es.elasticize_fu_out(path,name)

if __name__ == "__main__":
    logging.basicConfig(filename="/tmp/elastic.log",
                    level=logging.INFO,
                    format='%(levelname)s:%(asctime)s-%(name)s.%(funcName)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(os.path.basename(__file__))

    #STDOUT AND ERR REDIRECTIONS
    sys.stderr = stdErrorLog()
    sys.stdout = stdOutLog()


    #signal.signal(signal.SIGINT, signalHandler)
    
    eventQueue = Queue.Queue()

    conf=hltdconf.hltdConf('/etc/hltd.conf')
    dirname = sys.argv[1]
    dirname = os.path.basename(os.path.normpath(dirname))
    watchDir = os.path.join(conf.watch_directory,dirname)
    outputDir = conf.micromerge_output
    monDir = os.path.join(watchDir,"mon")
    tempDir = os.path.join(watchDir,ES_DIR_NAME)

    mask = inotify.IN_CLOSE_WRITE | inotify.IN_MOVED_TO
    monMask = inotify.IN_CLOSE_WRITE
    tempMask = inotify.IN_CLOSE_WRITE

    logger.info("starting elastic for "+dirname)

    try:
        os.makedirs(monDir)
    except OSError:
        pass
    try:
        os.makedirs(tempDir)
    except OSError:
        pass

    mr = None
    try:
        #starting inotify thread
        mr = MonitorRanger()
        mr.setEventQueue(eventQueue)
        mr.register_inotify_path(watchDir,mask)
        mr.register_inotify_path(monDir,monMask)
        mr.register_inotify_path(tempDir,tempMask)
        mr.start_inotify()

        es = elasticBand.elasticBand('http://localhost:9200',dirname)

        #starting elasticCollector thread
        ec = elasticCollector(ES_DIR_NAME)
        ec.setSource(eventQueue)
        ec.start()

    except Exception as e:
        logger.exception(e)
        print traceback.format_exc()
        logger.error("when processing files from directory "+dirname)

    logging.info("Closing notifier")
    if mr is not None:
      mr.stop_inotify()

    logging.info("Quit")
    sys.exit(0)
