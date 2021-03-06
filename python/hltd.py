#!/bin/env python
from functools import cmp_to_key
import os,sys
#sys.path.append('/opt/hltd/python')
sys.path.append('/opt/hltd/scratch/python')
sys.path.append('/opt/hltd/lib')

import time
import logging
import subprocess
import threading

try:
  from CGIHTTPServer import CGIHTTPRequestHandler
  from BaseHTTPServer import HTTPServer
except: #py3
  from http.server import CGIHTTPRequestHandler
  from http.server import HTTPServer

import cgitb
import pwd
#import socket
#import random

#modules distributed with hltd
import prctl
import inotify._inotify as inotify

#modules which are part of hltd
from hltdconf import initConf
from inotifywrapper import InotifyWrapper

from HLTDCommon import restartLogCollector,restoreFUListOnBU
from Run import RunList
from ResourceRanger import ResourceRanger
from RunRanger import RunRanger
from MountManager import MountManager
import SystemMonitor

from elasticbu import BoxInfoUpdater
#from WebCtrl import WebCtrl

#shared info classes
class BoxInfo:
    def __init__(self):
        self.machine_blacklist=[]
        self.machine_whitelist=[]
        self.has_whitelist=False
        self.FUMap = {}
        self.boxdoc_version = 5
        self.updater = None

class ResInfo:

    def __init__(self,state):
       self.q_list = []
       self.num_excluded = 0
       self.num_allowed = 0
       self.idles = None
       self.used = None
       self.broken = None
       self.quarantined = None
       self.cloud = None
       self.nthreads = None
       self.nstreams = None
       self.expected_processes = None
       self.last_idlecount=0
       self.state = state

    def cleanup_resources(self):
        try:
            dirlist = os.listdir(self.cloud)
            for cpu in dirlist:
                self.resmove(self.cloud,self.idles,cpu)
            dirlist = os.listdir(self.broken)
            for cpu in dirlist:
                self.resmove(self.broken,self.idles,cpu)
            dirlist = os.listdir(self.used)
            for cpu in dirlist:
                self.resmove(self.used,self.idles,cpu)
            dirlist = os.listdir(self.quarantined)
            for cpu in dirlist:
                self.resmove(self.quarantined,self.idles,cpu)
            dirlist = os.listdir(self.idles)
            #quarantine files beyond use fraction limit (rounded to closest integer)
            self.calc_num_allowed(0)
            for i in range(0,int(self.num_excluded)):
                self.resmove(self.idles,self.quarantined,dirlist[i])
            return True
        except Exception as ex:
            logger.warning(str(ex))
            return False

    def calc_num_allowed(self,delta):
        new_tot = len(os.listdir(self.broken)+os.listdir(self.used)+os.listdir(self.idles) \
                      + os.listdir(self.quarantined)+os.listdir(self.cloud)) + delta
        self.num_excluded = int(round(new_tot*(1.-conf.resource_use_fraction)))
        self.num_allowed = new_tot-self.num_excluded

    def move_resources_to_cloud(self):
        dirlist = os.listdir(self.broken)
        for cpu in dirlist:
            self.resmove(self.broken,self.cloud,cpu)
        dirlist = os.listdir(self.used)
        for cpu in dirlist:
            self.resmove(self.used,self.cloud,cpu)
        dirlist = os.listdir(self.quarantined)
        for cpu in dirlist:
            self.resmove(self.quarantined,self.cloud,cpu)
        self.q_list=[]
        dirlist = os.listdir(self.idles)
        for cpu in dirlist:
            self.resmove(self.idles,self.cloud,cpu)
        dirlist = os.listdir(self.idles)
        for cpu in dirlist:
            self.resmove(self.idles,self.cloud,cpu)

    def has_active_resources(self):
        return len(os.listdir(self.broken))+len(os.listdir(self.used))+len(os.listdir(self.idles)) > 0

    def count_resources(self):
        return len(os.listdir(self.broken))+len(os.listdir(self.used))+len(os.listdir(self.idles)) \
              +len(os.listdir(self.quarantined))+len(os.listdir(self.cloud))

    def exists(self,core):
        if core in os.listdir(self.idles):return True
        if core in os.listdir(self.used):return True
        if core in os.listdir(self.broken):return True
        if core in os.listdir(self.quarantined):return True
        if core in os.listdir(self.cloud):return True
        return False

    def addResources(self,delta):
        full_list = os.listdir(self.broken)+os.listdir(self.used)+os.listdir(self.idles) \
                    + os.listdir(self.quarantined)+os.listdir(self.cloud)
        self.calc_num_allowed(delta)
        max_cpu = delta
        for index in range(0,len(full_list)+max_cpu):
          if delta==0:break
          if 'core'+str(index) in full_list:
            continue
          else:
            logger.info('adding resource ' + 'core'+str(index))
            with open(os.path.join(self.quarantined,'core'+str(index)),'w') as fi:pass
            #check against allowed resource fraction limits
            in_cloud =  self.state.cloud_mode and not self.state.entering_cloud_mode
            if index<self.num_allowed or in_cloud:
              #move to cloud if in cloud mode
              if in_cloud:
                self.resmove(self.quarantined,self.cloud,'core'+str(index))
              else:
                self.resmove(self.quarantined,self.idles,'core'+str(index))
            delta-=1
        return delta

    def updateIdles(self,delta,checkLast=True):

        newcount=delta+self.last_idlecount
        if newcount<0:newcount=0
        in_cloud =  self.state.cloud_mode and not self.state.entering_cloud_mode
        idledir = self.cloud if in_cloud else self.idles
        current = len(os.listdir(idledir))
        #if requested to remove if possible
        if not checkLast:
          newcount = current + delta
        if newcount==current:
            #already updated
            return 0
        self.calc_num_allowed(delta)
        if newcount>current:
            toAdd = newcount-current
            totAdd=toAdd
            index=0
            while toAdd:
                corename = 'core'+str(index)
                if not self.exists(corename):
                    with open(os.path.join(self.quarantined,corename),'a') as fi:pass #using quarantined + move
                    #check against allowed resource fraction limits
                    if index<self.num_allowed or in_cloud:
                      #also will unquarantine if resource is quarantined
                      self.resmove(self.quarantined,idledir,corename)
                    toAdd-=1
                index+=1
            self.calculate_threadnumber()
            return toAdd
        if newcount<current:
            def cmpfinv(x,y):
                if int(x[4:])<int(y[4:]): return 1
                elif int(x[4:])>int(y[4:]): return -1
                else:return 0
            invslist = sorted(os.listdir(idledir)+os.listdir(self.quarantined),key=cmp_to_key(cmpfinv))
            toDelete = current-newcount
            totDel=toDelete
            for i in invslist:
                logger.info('deleting ' + str(i))
                #cascade into a idle,quarantined and cloud
                try:
                  os.unlink(os.path.join(self.idles,i))
                  toDelete-=1
                except:
                  try:
                    os.unlink(os.path.join(self.quarantined,i))
                    toDelete-=1
                  except:
                    try:
                      os.unlink(os.path.join(self.cloud,i))
                      toDelete-=1
                    except:
                      logger.warning('unable to delete resource ' + str(i)) 
                if toDelete==0:break
            self.calculate_threadnumber()
            return -toDelete

    def calculate_threadnumber(self):
        idlecount = len(os.listdir(self.idles))+len(os.listdir(self.cloud))
        if conf.cmssw_threads_autosplit>0:
            self.nthreads = idlecount//conf.cmssw_threads_autosplit
            self.nstreams = idlecount//conf.cmssw_threads_autosplit
            if self.nthreads*conf.cmssw_threads_autosplit != self.nthreads:
                logger.error("idle cores can not be evenly split to cmssw threads")
        else:
            self.nthreads = conf.cmssw_threads
            self.nstreams = conf.cmssw_streams
        self.expected_processes = idlecount//self.nstreams
        self.last_idlecount=idlecount
        self.calc_num_allowed(0)

    def resmove(self,sourcedir,destdir,res):
        os.rename(os.path.join(sourcedir,res),os.path.join(destdir,res))

class StateInfo:
    def __init__(self):
        #states (suspended <-> normal <-> cloud)
        self.suspended = False
        self.cloud_mode = False
        #transitional
        self.entering_cloud_mode = False
        self.exiting_cloud_mode = False
        #imperative 
        self.abort_cloud_mode = False
        #flags
        #self.resources_blocked_flag = False
        self.disabled_resource_allocation = False
        self.masked_resources = False
        self.os_cpuconfig_change = 0
        self.lock = threading.Lock()
        self.isGlobalRun = False
        self.daqSystem = "N/A"
        self.daqInstance = "N/A"
        self.fuGroup = "N/A"

    #interfaces to the cloud igniter script
    def ignite_cloud(self):
        try:
            proc = subprocess.Popen([conf.cloud_igniter_path,'start'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out=proc.communicate()[0]
            if not isinstance(out,str): out = out.decode("utf-8")
            if proc.returncode==0:
                return True
            else:
                if proc.returncode>1:
                  logger.error("cloud igniter start returned code "+str(proc.returncode)+ ' and console output: ' + out)
                if proc.returncode==1:
                  logger.error("cloud igniter start returned exit code 1")

        except OSError as ex:
            if ex.errno==2:
                logger.warning(conf.cloud_igniter_path + ' is missing')
            else:
                logger.error("Failed to run cloud igniter start")
                logger.exception(ex)
        return False

    def extinguish_cloud(self,repeat=False):
        try:
            proc = subprocess.Popen([conf.cloud_igniter_path,'stop'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out=proc.communicate()[0]
            if not isinstance(out,str): out = out.decode("utf-8")
            if proc.returncode in [0,1]:
                return True
            else:
                if repeat: #retry once in case cloud script returns funny exit code
                  logger.warning("cloud igniter stop returned with "+str(proc.returncode)+". retry once..")
                  if len(out):logger.warning(out)
                  time.sleep(.1)
                  self.extinguish_cloud()
                else:
                  logger.error("cloud igniter stop returned with "+str(proc.returncode))
                  if len(out):logger.error(out)

        except OSError as ex:
            if ex.errno==2:
                logger.warning(conf.cloud_igniter_path + ' is missing')
            else:
                logger.error("Failed to run cloud igniter start")
                logger.exception(ex)
        return False

    def cloud_script_available(self):
        try:
            os.stat(conf.cloud_igniter_path)
            return True
        except:
            return False


    def cloud_status(self,reportExitCodeError=True):
        try:
            proc = subprocess.Popen([conf.cloud_igniter_path,'status'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out=proc.communicate()[0]
            if not isinstance(out,str): out = out.decode("utf-8")
            if proc.returncode >1 and proc.returncode != 14:
                if reportExitCodeError:
                    logger.error("cloud igniter status returned error code "+str(proc.returncode) + " output: "+str(out))
                else:
                    logger.warning("cloud igniter status returned error code "+str(proc.returncode) + " output: "+str(out))
        except OSError as ex:
            if ex.errno==2:
                logger.warning(conf.cloud_igniter_path + ' is missing')
            else:
                logger.error("Failed to run cloud igniter start")
                logger.exception(ex)
            return 100
        #script returns 0/1 if cloud is running/not running. invert this
        if proc.returncode == 0:return 1
        elif proc.returncode == 1: return 0
        else: return proc.returncode


#load configuration
def setFromConf(myinstance,resInfo):

    global conf
    global logger

    conf=initConf(myinstance)

    #for running from symbolic links
    watch_directory = os.readlink(conf.watch_directory) if os.path.islink(conf.watch_directory) else conf.watch_directory
    conf.watch_directory = watch_directory

    """
    the line below is a VERY DIRTY trick to address the fact that
    BU resources are dynamic hence they should not be under /etc
    """
    if conf.role == 'bu':
        resource_base = os.path.join(conf.watch_directory,'appliance')
    else:
        resource_base = conf.resource_base
    resource_base = os.readlink(resource_base) if os.path.islink(resource_base) else resource_base
    conf.resource_base = resource_base

    if conf.role == 'fu':
        resInfo.idles = os.path.join(resource_base,'idle/')
        resInfo.used = os.path.join(resource_base,'online/')
        resInfo.broken = os.path.join(resource_base,'except/')
        resInfo.quarantined = os.path.join(resource_base,'quarantined/')
        resInfo.cloud = os.path.join(resource_base,'cloud/')

    #prepare log directory
    if myinstance!='main':
        if not os.path.exists(conf.log_dir):
            os.makedirs(conf.log_dir)
        if not os.path.exists(os.path.join(conf.log_dir,'pid')):
            os.makedirs(os.path.join(conf.log_dir,'pid'))
        os.chmod(conf.log_dir,0o777)
        os.chmod(os.path.join(conf.log_dir,'pid'),0o777)

    logging.basicConfig(filename=os.path.join(conf.log_dir,"hltd.log"),
                    level=conf.service_log_level,
                    format='%(levelname)s:%(asctime)s - %(funcName)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(os.path.basename(__file__))

    #ensure to setup properly permissions for log files written to by unpriviledged child processes
    pw_record = pwd.getpwnam(conf.user)
    try:os.chown(os.path.join(conf.log_dir,"anelastic.log"), pw_record.pw_uid, pw_record.pw_gid)
    except:pass
    try:os.chown(os.path.join(conf.log_dir,"elastic.log"), pw_record.pw_uid, pw_record.pw_gid)
    except:pass
    try:os.chown(os.path.join(conf.log_dir,"elasticbu.log"), pw_record.pw_uid, pw_record.pw_gid)
    except:pass

    conf.dump()

#main class
class hltd:
    def __init__(self, instance):
        self.instance=instance

    def run(self):
        """
        if role is not defined in the configuration (which it shouldn't)
        infer it from the name of the machine
        """

        #read configuration file
        state = StateInfo()
        resInfo = ResInfo(state)
        setFromConf(self.instance,resInfo)

        logger.info(" ")
        logger.info(" ")
        logger.info("[[[[ ---- hltd start : instance " + self.instance + " ---- ]]]]")
        logger.info(" ")

        if conf.enabled==False:
            logger.warning("Service is currently disabled.")
            sys.exit(1)

        nsslock = threading.Lock()
        resource_lock = threading.Lock()
        mm = None
        #no static mountpoint if dynamic_mounts parameter is set
        if not conf.dynamic_mounts or conf.role == 'bu':
          mm = MountManager(conf)

        if conf.role == 'fu':

            """
            cleanup resources
            """
            res_in_cloud = len(os.listdir(resInfo.cloud))>0
            def cloud_check1_maybe():
              while True:
                #switch to cloud mode if cloud files are found (e.g. machine rebooted while in cloud)
                #NOTE: this runs early to activate cloud even if mountpoints are not ready
                if res_in_cloud:
                    logger.warning('found cores in cloud. this session will start in the cloud mode')
                    try:
                        resInfo.move_resources_to_cloud()
                    except Exception as ex:
                        logger.warning(str(ex))

                    state.cloud_mode=True
                    #TODO:what if cloud mode switch fails?
                    cloud_st = state.cloud_status()
                    if not cloud_st:#cloud off,switch on
                        result = state.ignite_cloud()
                        break
                    elif cloud_st==1:#cloud is already on
                        break
                    elif cloud_st>1:#error,try to switch off cloud and switch HLT mode
                      time.sleep(1)
                      logger.warning("cloud status returned error. going to try to retry check")
                      cloud_st = state.cloud_status()

                      if not cloud_st:#cloud off,switch on
                        result = state.ignite_cloud()
                        break
                      elif cloud_st==1:#cloud is already on
                        break
                      elif cloud_st>1:#error,try to switch off cloud and switch HLT mode
 
                        logger.warning("cloud status returned error. going to try to stop cloud")
                        stop_st = state.extinguish_cloud(repeat=True)
                      #trusting the extinguish function return code
                        if not stop_st:
                          logger.error("failed deactivating cloud")
                          #script error, leaving cores in cloud mode
                          break
                state.cloud_mode=False
                if resInfo.cleanup_resources()==True:break
                time.sleep(0.1)
                logger.warning("retrying cleanup_resources")

            cloud_check1_maybe()

            #init (shoudl not change later)
            resInfo.calculate_threadnumber()

            #ensure that working directory is ready
            try:os.makedirs(conf.watch_directory)
            except:pass

            #run class init
            runList = RunList()

            #start monitor thread to get fu-box-status docs inserted early in case of mount problems
            boxInfo = BoxInfo()
            num_cpus_initial=-1

            def cloud_check2_maybe():
                """
                recheck mount points
                """
                #switch to cloud mode if active, but hltd did not have cores in cloud directory in the last session
                if not res_in_cloud and state.cloud_script_available():
                    cl_status = state.cloud_status()
                    cnt = 5
                    while not (cl_status == 1 or cl_status == 0 or cl_status==66) and cnt>0:
                      time.sleep(1)
                      cnt-=1
                      cl_status = state.cloud_status()
                    if cl_status >0:
                        if cl_status==66:
                          logger.warning('cloud status code 66 (no NOVA stack). Will run in HLT mode')
                        else:
                          if cl_status > 1:
                            logger.error('cloud status script returns error exit code (status:'+str(cl_status)+') after 5 attempts. Trying to deactivate cloud')
                            stop_st = state.extinguish_cloud(repeat=True)
                            if stop_st==True:
                              #cloud was stopped, can continue in HLT mode
                              pass
                            else:
                              logger.error('cloud deactivate failed. HLT mode will be disabled')
                              resInfo.move_resources_to_cloud()
                              state.cloud_mode=True
                          else:
                            logger.warning("cloud services are running on this host at hltd startup, switching to cloud mode")
                            resInfo.move_resources_to_cloud()
                            state.cloud_mode=True

            #first check before mounting, to set resources to cloud (if cloud mode) eatly on for monitoring even if mountpoints are not ready
            cloud_check2_maybe()

            #cleanup old directory
            if conf.watch_directory.startswith('/fff/'):
                p = subprocess.Popen("rm -rf " + conf.watch_directory+'/*',shell=True)
                p.wait()


            if mm and not mm.cleanup_mountpoints(nsslock):
                logger.fatal("error mounting - terminating service")
                os._exit(10)

            #check after mountpoint (which depends on BU availability and does not have bound duration
            res_in_cloud = len(os.listdir(resInfo.cloud))>0
            if not state.cloud_mode:
                #cloud was OFF. Check if anything changed (resources moved by hand, or scripts started by hand)
                cloud_check1_maybe()
                cloud_check2_maybe()
            if state.cloud_mode:
                logger.info("init finished - cloud mode active")
            else:
                logger.info("init finished - HLT mode set")
            #TODO:check if cloud was turned OFF during mountpoint check


            #recursively remove any stale run data and other commands in the FU watch directory
            #if conf.watch_directory.strip()!='/':
            #    p = subprocess.Popen("rm -rf " + conf.watch_directory.strip()+'/{run*,end*,quarantined*,exclude,include,suspend*,populationcontrol,herod,logrestart,emu*}',shell=True)
            #    p.wait()


            #count core files
            if conf.dynamic_resources: num_cpus_initial = resInfo.count_resources()

        else: #BU mode
            #run class init
            runList = RunList()
            #start monitor thread
            boxInfo = BoxInfo()
            num_cpus_initial=-1

        #start monitor after all state checks/migration have finished
        sm = SystemMonitor.system_monitor(conf,state,resInfo,runList,mm,boxInfo,num_cpus_initial)

        #startup es log collector
        logCollector = None
        if conf.use_elasticsearch == True:
            time.sleep(.2)
            try:
              restartLogCollector(conf,logger,logCollector,self.instance)
            except:
              logger.error("can not spawn log collector. terminating..")
              os._exit(1)

        #BU mode threads
        if conf.role == 'bu':

            #restore blacklist and whitelist from cache if service restarted
            boxInfo.machine_blacklist=restoreFUListOnBU(conf,logger,"blacklist")
            boxInfo.machine_whitelist=restoreFUListOnBU(conf,logger,"whitelist")

            mm.ramdisk_submount_size=0
            if self.instance == 'main':
                #if there are other instance mountpoints in ramdisk, they will be subtracted from size estimate
                mm.submount_size(conf.watch_directory)

            #start boxinfo elasticsearch updater
            try:os.makedirs(os.path.join(conf.resource_base,'dn'))
            except:pass
            try:os.makedirs(os.path.join(conf.resource_base,'boxes'))
            except:pass
            if conf.use_elasticsearch == True:
                boxInfo.updater = BoxInfoUpdater(conf,nsslock,boxInfo.boxdoc_version)
                boxInfo.updater.start()

        rr = ResourceRanger(conf,state,resInfo,runList,boxInfo,sm,resource_lock)

        #init resource ranger
        try:
            if conf.role == 'bu':
                imask  = inotify.IN_CLOSE_WRITE | inotify.IN_DELETE | inotify.IN_CREATE | inotify.IN_MOVED_TO
                rr.register_inotify_path(conf.resource_base, imask)
                rr.register_inotify_path(os.path.join(conf.resource_base,'boxes'), imask)
            else:
                imask  = inotify.IN_MOVED_TO
                rr.register_inotify_path(os.path.join(conf.resource_base,'idle'), imask)
                rr.register_inotify_path(os.path.join(conf.resource_base,'cloud'), imask)
                rr.register_inotify_path(os.path.join(conf.resource_base,'except'), imask)
                rr.register_inotify_path(os.path.join(conf.resource_base,'quarantined'), imask)
            rr.start_inotify()
            logger.info("started ResourceRanger - watch_directory "+conf.resource_base)
        except Exception as ex:
            logger.error("Exception caught in starting ResourceRanger notifier")
            logger.error(ex)
            os._exit(1)


        #start monitoring new runs
        runRanger = RunRanger(self.instance,conf,state,resInfo,runList,rr,mm,sm,logCollector,nsslock,resource_lock)
        runRanger.register_inotify_path(conf.watch_directory,inotify.IN_CREATE)
        runRanger.start_inotify()
        logger.info("started RunRanger  - watch_directory " + conf.watch_directory)

        #resource notification enabled with inotify set up
        sm.allowResourceNotification()

        try:
            cgitb.enable(display=0, logdir="/tmp")
            handler = CGIHTTPRequestHandler
            #handler = WebCtrl(self) #to be tested later
            # the following allows the base directory of the http
            # server to be 'conf.watch_directory, which is writeable
            # to everybody
            if os.path.exists(conf.watch_directory+'/cgi-bin'):
                os.remove(conf.watch_directory+'/cgi-bin')
            os.symlink('/opt/hltd/cgi',conf.watch_directory+'/cgi-bin')

            handler.cgi_directories = ['/cgi-bin']
            logger.info("starting http server on port "+str(conf.cgi_port))
            httpd = HTTPServer(("", conf.cgi_port), handler)

            logger.info("hltd serving at port "+str(conf.cgi_port)+" with role "+conf.role)
            os.chdir(conf.watch_directory)
            logger.info("[[[[ ---- hltd instance " + self.instance + ": init complete, starting httpd ---- ]]]]")
            logger.info("")
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("stop signal detected")
            runList.clearOngoingRunFlags()
            aRuns =  runList.getActiveRuns()
            if len(aRuns)>0:
                logger.info("terminating all ongoing runs")
                for run in aRuns:
                    if conf.role=='fu':
                        run.Shutdown(True,True)
                    elif conf.role=='bu':
                        run.ShutdownBU()
                logger.info("terminated all ongoing runs")
            runRanger.stop_inotify()
            rr.stop_inotify()
            if boxInfo.updater is not None:
                logger.info("stopping boxinfo updater")
                boxInfo.updater.stop()
            if logCollector is not None:
                logger.info("terminating logCollector")
                logCollector.terminate()
            logger.info("stopping system monitor")
            rr.stop_managed_monitor()
            logger.info("closing httpd socket")
            httpd.socket.close()
            logger.info(threading.enumerate())
            logger.info("unmounting mount points")
            if conf.role == 'fu' and mm:
                if not mm.cleanup_mountpoints(nsslock,remount=False):
                    time.sleep(1)
                    mm.cleanup_mountpoints(nsslock,remount=False)

            logger.info("shutdown of service (main thread) completed")
            os._exit(0)
        except Exception as ex:
            logger.info("exception encountered in operating hltd")
            logger.info(ex)
            runRanger.stop_inotify()
            rr.stop_inotify()
            rr.stop_managed_monitor()
            raise

    def webHandler(self,option):
        logger.info('TEST:received option ' + option)

if __name__ == "__main__":
    import setproctitle
    setproctitle.setproctitle('hltd')

    p_instance = "main"
    if len(sys.argv)>1:
      p_instance=sys.argv[1]

    daemon = hltd(p_instance)
    os.umask(0)
    daemon.run()
