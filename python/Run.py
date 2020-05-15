import os
import sys
import shutil
import time
import json
import subprocess
import threading
import datetime
import demote
import prctl
from signal import SIGKILL
import logging

import Resource
from HLTDCommon import updateFUListOnBU,deleteFUListOnBU,dqm_globalrun_filepattern
from MountManager import  find_nfs_mount_addr
from setupES import setupES

this_machine = os.uname()[1]
this_machine_short = os.uname()[1].split('.')[0]

def preexec_function():
    dem = demote.demote(conf.user)
    dem()
    prctl.set_pdeathsig(SIGKILL)
    #    os.setpgrp()

class RunList:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.runs = []

    def add(self,runObj):
        runNumber = runObj.runnumber
        check = [x for x in self.runs[:] if runNumber == x.runnumber]
        if len(check):
            raise Exception("Run "+str(runNumber)+" already exists")
        #doc = {runNumber:runObj}
        #self.runs.append(doc)
        self.runs.append(runObj)

    def remove(self,runNumber):
        #runs =  map(lambda x: x.keys()[0]==runNumber)
        runs =  [x for x in self.runs[:] if x.runnumber==runNumber]
        if len(runs)>1:
            self.logger.error("Multiple runs entries for "+str(runNumber)+" were found while removing run")
        for run in runs[:]: self.runs.pop(self.runs.index(run))

    def getOngoingRuns(self):
        #return map(lambda x: x[x.keys()[0]], filter(lambda x: x.is_ongoing_run==True,self.runs))
        return [x for x in self.runs[:] if x.is_ongoing_run==True]

    def getQuarantinedRuns(self):
        return [x for x in self.runs[:] if x.pending_shutdown==True]

    def getActiveRuns(self):
        #return map(lambda x.runnumber: x, self.runs)
        return self.runs[:]

    def getActiveRunNumbers(self):
        return [x.runnumber for x in self.runs[:]]

    def getLastRun(self):
        try:
            return self.runs[-1]
        except:
            return None

    def getLastOngoingRun(self):
        try:
            return self.getOngoingRuns()[-1]
        except:
            return None

    def getRun(self,runNumber):
        try:
            return [x for x in self.runs[:] if x.runnumber==runNumber][0]
        except:
            return None

    def isLatestRun(self,runObj):
        return self.runs[-1] == runObj
        #return len(filter(lambda x: x.runnumber>runObj.runnumber,self.runs))==0

    def getStateDoc(self):
        docArray = []
        for runObj in self.runs[:]:
            docArray.append({'run':runObj.runnumber,'totalRes':runObj.n_used,'qRes':runObj.n_quarantined,'ongoing':runObj.is_ongoing_run,'errors':runObj.num_errors,'errorsRes':runObj.num_errors_res})
        return docArray

    def clearOngoingRunFlags(self):
        for runObj in self.runs[:]:
            runObj.is_ongoing_run=False


class Run:

    def __init__(self,nr,dirname,bu_base_ram_dirs,bu_dir,bu_output_base_dir,instance,confClass,stateInfo,resInfo,runList,rr,nsslock,resource_lock):

        self.logger = logging.getLogger(self.__class__.__name__)
        self.pending_shutdown=False
        self.is_ongoing_run=True
        self.num_errors = 0
        self.num_errors_res = 0

        self.runnumber = nr
        self.bu_base_ram_dirs = bu_base_ram_dirs
        self.dirname = dirname
        self.instance = instance
        self.state = stateInfo
        self.resInfo = resInfo
        self.runList = runList
        self.rr = rr
        self.nsslock = nsslock
        self.resource_lock = resource_lock
        self.send_bu = False

        global conf
        conf = confClass
        self.conf = conf

        self.online_resource_list = []
        self.online_resource_list_join = []
        self.anelastic_monitor = None
        self.elastic_monitor = None
        self.elastic_test = None

        self.arch = None
        self.version = None
        self.menu_path = None
        self.fasthadd_installation_path = 'None'

        self.buDataAddr = 'None'
        self.transferMode = None
        self.waitForEndThread = None
        self.beginTime = datetime.datetime.now()
        self.anelasticWatchdog = None
        self.elasticBUWatchdog = None
        self.completedChecker = None
        self.runShutdown = None
        self.threadEvent = threading.Event()
        self.stopThreads = False

        #stats on usage of resources
        self.n_used = 0
        self.n_quarantined = 0
        self.skip_notification_list = []
        self.pending_contact = []
        self.asyncContactThread = None
        self.threadEventContact = threading.Event()

        self.clear_quarantined_count = 0
        self.not_clear_quarantined_count = 0
        self.inputdir_exists = False


        hltInfoDetected = False

        #TODO:raise from runList
        #            if int(self.runnumber) in active_runs:
        #                raise Exception("Run "+str(self.runnumber)+ "already active")


        if conf.role == 'fu':
            self.changeMarkerMaybe(Resource.RunCommon.STARTING)
        
            hlt_directory = os.path.join(bu_dir,conf.menu_directory)
            paramfile_path = os.path.join(hlt_directory,conf.paramfile_name)
            self.menu_path = os.path.join(hlt_directory,conf.menu_name)
            self.hltinfofile_path = os.path.join(hlt_directory,conf.hltinfofile_name) 

            readMenuAttempts=0
            def paramsPresent():
                return os.path.exists(hlt_directory) and os.path.exists(self.menu_path) and os.path.exists(paramfile_path)

            paramsDetected = False
            while not conf.dqm_machine:
              #polling for HLT menu directory
              if paramsPresent():
                try:
                    with open(paramfile_path,'r') as fp:
                        fffparams = json.load(fp)

                        self.arch = fffparams['SCRAM_ARCH']
                        self.version = fffparams['CMSSW_VERSION']
                        self.transferMode = fffparams['TRANSFER_MODE']
                        paramsDetected = True
                        self.logger.info("Run " + str(self.runnumber) + " uses " + self.version + " ("+self.arch + ") with " + str(conf.menu_name) + ' transferDest:'+self.transferMode)

                    hltInfoDetected = self.getHltInfoParameters()

                    #finish if fffParams found. hltinfo is still optionall
                    break

                except ValueError as ex:
                    if readMenuAttempts>50:
                        self.logger.exception(ex)
                        break
                except Exception as ex:
                    if readMenuAttempts>50:
                        self.logger.exception(ex)
                        break

              else:
                if readMenuAttempts>50:
                    if not os.path.exists(bu_dir):
                        self.logger.info("FFF parameter or HLT menu files not found in ramdisk - BU run directory is gone")
                    else:
                        self.logger.error('RUN:'+str(self.runnumber) + " - FFF parameter or HLT menu files not found in ramdisk")
                    break
              readMenuAttempts+=1
              time.sleep(.1)
            #end loop

            if not paramsDetected:
                self.arch = conf.cmssw_arch
                self.version = conf.cmssw_default_version
                self.menu_path = conf.test_hlt_config1
                self.transferMode = 'null'
                self.logger.warning("Using default values for run " + str(self.runnumber) + ": " + self.version + " (" + self.arch + ") with " + self.menu_path)

            #give this command line parameter quoted in case it is empty
            if not len(self.transferMode):self.transferMode='null'

            #backup HLT menu and parameters
            try:
                hltTargetName = 'HltConfig.py_run'+str(self.runnumber)+'_'+self.arch+'_'+self.version+'_'+self.transferMode
                shutil.copy(self.menu_path,os.path.join(conf.log_dir,'pid',hltTargetName))
            except:
                self.logger.warning('Unable to backup HLT menu')

            if not conf.dqm_machine:
                #run cmspkg to detect which fasthadd package version is used with this CMSSW
                conf.cmssw_script_location+'/fastHaddVersion.sh'
                p = subprocess.Popen([conf.cmssw_script_location+'/fastHaddVersion.sh',conf.cmssw_base,self.arch,self.version], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ret = p.communicate()
                if p.returncode==0:
                    self.fasthadd_installation_path = ret[0].decode()
                    self.logger.info('RUN:'+str(self.runnumber)+" fasthHaddVersion returned: "+ self.fasthadd_installation_path)
                else:
                    self.logger.error('RUN:'+str(self.runnumber)+" fastHadd not found. stdout=" + ret[0].decode() + " stderr=" + ret[1].decode())

        if not conf.dqm_machine and not conf.local_mode:
            try:
                buDataAddrTmp = find_nfs_mount_addr(bu_base_ram_dirs[0])
                if self.buDataAddr is None:
                    raise Exception("BU data network mount point not found")
                self.buDataAddr = buDataAddrTmp
            except Exception as ex:
                #if this fails, give up right away to avoid starting processes without proper BU data address
                self.logger.exception(ex)
                return


        self.rawinputdir = None

        if conf.role == "bu":
            mainDir = os.path.join(conf.watch_directory,'run'+ str(self.runnumber).zfill(conf.run_number_padding))
            hlt_directory = os.path.join(mainDir,'hlt')
            self.hltinfofile_path = os.path.join(hlt_directory,conf.hltinfofile_name) 

            readParamsAttempts=0
            def infoParamsPresent():
                return os.path.exists(hlt_directory) and os.path.exists(self.hltinfofile_path)

            while not conf.dqm_machine:
                #polling for HLT info file
                if infoParamsPresent():
                      hltInfoDetected = self.getHltInfoParameters()
                      break
                else:
                    if readParamsAttempts>10:
                        if not os.path.exists(mainDir):
                            self.logger.info("hltinfo file not found in ramdisk - BU run directory is gone")
                        else:
                            self.logger.warning('RUN:'+str(self.runnumber) + " - hltinfo files not found in ramdisk")
                        break
                readParamsAttempts+=1
                time.sleep(.1)

            try:
                self.rawinputdir = conf.watch_directory+'/run'+str(self.runnumber).zfill(conf.run_number_padding)
                os.stat(self.rawinputdir)
                self.inputdir_exists = True
            except Exception as ex:
                self.logger.error('RUN:'+str(self.runnumber)+" - failed to stat "+self.rawinputdir)
            try:
                os.mkdir(self.rawinputdir+'/mon')
            except Exception as ex:
                self.logger.error('RUN:'+str(self.runnumber)+" - could not create mon dir inside the run input directory")
        else:
            self.rawinputdir= os.path.join(bu_base_ram_dirs[0],'run' + str(self.runnumber).zfill(conf.run_number_padding))

        #verify existence of the input directory
        if conf.role=='fu':
            if not paramsDetected and not conf.dqm_machine:
                try:
                    os.stat(self.rawinputdir)
                    self.inputdir_exists = True
                except:
                    self.logger.warning("unable to stat raw input directory for run "+str(self.runnumber))
                    return
            else:
                self.inputdir_exists = True

        nsslock_acquired=False
        if conf.use_elasticsearch == True:
            try:
                if conf.role == "bu":
                    self.nsslock.acquire()
                    nsslock_acquired=True
                    self.logger.info("starting elasticbu.py with arguments:"+self.dirname)
                    elastic_args = ['/opt/hltd/scratch/python/elasticbu.py',str(self.runnumber),self.instance]
                else:
                    if self.buDataAddr != 'None':
                      appliance_name = self.buDataAddr.split('.')[0]
                      if self.buDataAddr.endswith('.cern.ch'): appliance_name =  self.buDataAddr #VM test setup
                    else:
                      appliance_name="unknown"

                    self.logger.info("starting elastic.py with arguments:"+self.dirname)
                    elastic_args = ['/opt/hltd/scratch/python/elastic.py',str(self.runnumber),self.dirname,self.rawinputdir+'/mon',appliance_name,str(self.resInfo.expected_processes)]

                self.elastic_monitor = subprocess.Popen(elastic_args,
                                                        preexec_fn=preexec_function,
                                                        close_fds=True
                                                        )
            except OSError as ex:
                self.logger.error('RUN:'+str(self.runnumber)+" - failed to start elasticsearch client (OSError)")
                self.logger.error(ex)
            except Exception as ex:
                self.logger.error('RUN:'+str(self.runnumber)+" - failed to start elasticsearch client (Exception)")
                self.logger.exception(ex)
            finally:
                if nsslock_acquired:
                    self.nsslock.release()

        if conf.role == "fu" and not conf.dqm_machine:
            try:
                self.logger.info("starting anelastic.py with arguments:"+self.dirname)
                elastic_args = ['/opt/hltd/scratch/python/anelastic.py',str(self.runnumber),self.dirname,self.rawinputdir,bu_output_base_dir,self.fasthadd_installation_path]
                self.anelastic_monitor = subprocess.Popen(elastic_args,
                                                    preexec_fn=preexec_function,
                                                    close_fds=True
                                                    )
            except OSError as ex:
                self.logger.fatal('RUN:'+str(self.runnumber)+" - will terminate service after failing to start anelastic.py client (OSError):")
                self.logger.exception(ex)
                self.logger.info('exiting...')
                time.sleep(1)
                os._exit(2)
            except Exception as ex:
                self.logger.fatal('RUN:'+str(self.runnumber)+" - will terminate service after failing to start anelastic.py client (Exception):")
                self.logger.exception(ex)
                self.logger.info('exiting...')
                time.sleep(1)
                os._exit(2)

    def __del__(self):
        self.logger.info('Run '+ str(self.runnumber) +' object __del__ runs')
        self.stopThreads=True
        self.threadEvent.set()
        self.stopAsyncContact()
        if self.completedChecker:
            try:
                self.completedChecker.join()
            except RuntimeError:
                pass
        if self.elasticBUWatchdog:
            try:
                self.elasticBUWatchdog.join()
            except RuntimeError:
                pass
        if self.runShutdown:
            self.joinShutdown()

        self.logger.info('Run '+ str(self.runnumber) +' object __del__ has completed')

    def countOwnedResourcesFrom(self,resourcelist):
        ret = 0
        try:
            for p in self.online_resource_list:
                for c in p.cpu:
                    for resourcename in resourcelist:
                        if resourcename == c:
                            ret+=1
        except:pass
        return ret

    def AcquireResource(self,resourcenames,fromstate):
        fromDir = conf.resource_base+'/'+fromstate+'/'
        try:
            self.logger.debug("Trying to acquire resource "
                          +str(resourcenames)
                          +" from "+fromstate)

            for resourcename in resourcenames:
                self.resInfo.resmove(fromDir,self.resInfo.used,resourcename)
                self.n_used+=1
            #TODO:fix core pairing with resource.cpu list (otherwise - restarting will not work properly)
            if not [x for x in self.online_resource_list if sorted(x.cpu)==sorted(resourcenames)]:
                self.logger.debug("resource(s) "+str(resourcenames)
                              +" not found in online_resource_list, creating new")
                newres = Resource.OnlineResource(self,resourcenames,self.resource_lock)
                self.online_resource_list.append(newres)
                self.online_resource_list_join.append(newres)
                return newres
            self.logger.debug("resource(s) "+str(resourcenames)
                          +" found in online_resource_list")
            return [x for x in self.online_resource_list if sorted(x.cpu)==sorted(resourcenames)][0]
        except Exception as ex:
            self.logger.info("exception encountered in looking for resources")
            self.logger.info(ex)

    def MatchResource(self,resourcenames):
        for res in self.online_resource_list:
            #first resource in the list is the one that triggered inotify event
            if resourcenames[0] in res.cpu:
                found_all = True
                for name in res.cpu:
                    if name not in resourcenames:
                        found_all = False
                if found_all:
                    return res.cpu
        return None

    def CreateResource(self,resourcenames,f_ip):
        newres = Resource.OnlineResource(self,resourcenames,self.resource_lock,f_ip)
        self.online_resource_list.append(newres)
        self.online_resource_list_join.append(newres)
        #self.online_resource_list[-1].ping() #@@MO this is not doing anything useful, afaikt

    def ReleaseResource(self,res):
        self.online_resource_list.remove(res)

    def AcquireResources(self,mode):
        self.logger.info("acquiring resources from "+conf.resource_base)
        res_dir = self.resInfo.idles if conf.role == 'fu' else os.path.join(conf.resource_base,'boxes')
        try:
            dirlist = os.listdir(res_dir)
            self.logger.info(str(dirlist))
        except Exception as ex:
            self.logger.info("exception encountered in looking for resources")
            self.logger.info(ex)
        current_time = time.time()
        count = 0
        cpu_group=[]

        hltdir = os.path.join(self.dirname,'hlt')
        blpath = os.path.join(self.dirname,'hlt','blacklist')
        wlpath = os.path.join(self.dirname,'hlt','whitelist')
        if conf.role=='bu':
            attempts=100
            while not os.path.exists(hltdir) and attempts>0:
                time.sleep(0.05)
                attempts-=1
                if attempts<=0:
                    self.logger.error('RUN:'+str(self.runnumber)+' - timeout waiting for directory '+ hltdir)
                    break
            if os.path.exists(blpath):
                update_success,self.rr.boxInfo.machine_blacklist = updateFUListOnBU(conf,self.logger,blpath,'blacklist')
            else:
                self.logger.warning('RUN:'+str(self.runnumber)+" - unable to find blacklist file in "+hltdir + ". Starting without blacklist")
                update_success = True
                self.rr.boxInfo.machine_blacklist = []
                #delete blacklist file from ramdisk and backup, disable blacklist
                deleteFUListOnBU(blpath,'blacklist')

            if os.path.exists(wlpath):
                self.send_bu = True
                self.rr.boxInfo.has_whitelist,self.rr.boxInfo.machine_whitelist = updateFUListOnBU(conf,self.logger,wlpath,'whitelist')
            else:
                self.logger.warning('RUN:'+str(self.runnumber)+" - unable to find whitelist file in "+hltdir+ ". Starting without whitelist")
                #delete blacklist file from ramdisk and backup, disable whitelist
                self.rr.boxInfo.has_whitelist = False
                self.rr.boxInfo.machine_whitelist = []
                deleteFUListOnBU(wlpath,'whitelist')

        for cpu in dirlist:
            #skip self
            f_ip = None
            if conf.role=='bu':
                if cpu == this_machine:continue
                if cpu in self.rr.boxInfo.machine_blacklist:
                    self.logger.info("skipping blacklisted resource "+str(cpu))
                    continue

                if self.rr.boxInfo.has_whitelist and cpu not in self.rr.boxInfo.machine_whitelist:
                    self.logger.info("skipping non-whitelisted resource "+str(cpu))
                    continue

                is_stale,f_ip = self.checkStaleResourceFileAndIP(os.path.join(res_dir,cpu)) 
                if is_stale:
                    self.logger.error('RUN:'+str(self.runnumber)+" - skipping stale resource "+str(cpu))
                    continue

            count = count+1
            try:
                age = current_time - os.path.getmtime(os.path.join(res_dir,cpu))
                cpu_group.append(cpu)
                if conf.role == 'fu':
                    if count == self.resInfo.nstreams:
                        self.AcquireResource(cpu_group,'idle')
                        cpu_group=[]
                        count=0
                else:
                    self.logger.info("found resource "+cpu+" which is "+str(age)+" seconds old")
                    if age < 10:
                        cpus = [cpu]
                        self.CreateResource(cpus,f_ip)
            except Exception as ex:
                self.logger.error('RUN:'+str(self.runnumber)+' - encountered exception in acquiring resource '+str(cpu)+':'+str(ex))

        #look also at whitelist entries which are not currently found in box directory
        if conf.role == 'bu' and self.rr.boxInfo.has_whitelist:
            for cpu in [x for x in self.rr.boxInfo.machine_whitelist if x not in dirlist]: 
                if cpu == this_machine:continue
                if cpu in self.rr.boxInfo.machine_blacklist:
                    self.logger.error("skipping blacklisted resource "+str(cpu)+" which is also in whitelist")
                    continue
                count = count+1
                self.logger.info("creating resource "+cpu+" which is only in whitelist")
                try:
                    self.skip_notification_list.append(cpu)
                    self.CreateResource([cpu],None)
                except Exception as ex:
                    self.logger.error('RUN:'+str(self.runnumber)+' - encountered exception in assigning whitelisted resource '+str(cpu)+':'+str(ex))

        return True

    def checkStaleResourceFileAndIP(self,resourcepath):
        f_ip=None
        try:
            with open(resourcepath,'r') as fi:
                doc = json.load(fi)
                try:f_ip = doc['ip']
                except:pass
                if doc['detectedStaleHandle']==True:
                    return True,f_ip
        except:
            time.sleep(.05)
            try:
                with open(resourcepath,'r') as fi:
                    doc = json.load(fi)
                    try:f_ip = doc['ip']
                    except:pass
                    if doc['detectedStaleHandle']==True:
                        return True,f_ip
            except:
                self.logger.warning('can not parse ' + str(resourcepath))
        return False,f_ip

    def CheckTemplate(self,run=None):
        if conf.role=='bu' and conf.use_elasticsearch and conf.update_es_template:
            self.logger.info("checking ES template")
            try:
                #new: try to create index with template mapping after template check
                new_index_name = 'run'+str(self.runnumber)+'_'+conf.elastic_index_suffix
                setupES(es_server_url='http://'+conf.es_local+':9200',forceReplicas=conf.force_replicas,forceShards=conf.force_shards,create_index_name=new_index_name,subsystem=conf.elastic_index_suffix)
            except Exception as ex:
                self.logger.error('RUN:'+str(self.runnumber)+" - unable to check run appliance template:"+str(ex))

    def Start(self):
        self.is_ongoing_run = True
        #create mon subdirectory before starting
        try:
            os.makedirs(os.path.join(self.dirname,'mon'))
        except OSError:
            pass
        #start/notify run for each resource
        if conf.role == 'fu':
            for resource in self.online_resource_list:
                self.logger.info('start run '+str(self.runnumber)+' on cpu(s) '+str(resource.cpu))
                #this is taken only with acquired resource_lock. It will be released temporarily within this function:
                self.StartOnResource(resource,is_locked=True)

            if not conf.dqm_machine:
                self.changeMarkerMaybe(Resource.RunCommon.ACTIVE)
                #start safeguard monitoring of anelastic.py
                self.startAnelasticWatchdog()

        elif conf.role == 'bu':
            for resource in self.online_resource_list:
                self.logger.info('start run '+str(self.runnumber)+' on resources '+str(resource.cpu))
                resource.NotifyNewRunStart(self.runnumber,self.send_bu)
            #update begin time at this point
            self.beginTime = datetime.datetime.now()
            for resource in self.online_resource_list:
                resource.NotifyNewRunJoin()
                if not resource.ok:
                  self.pending_contact.append(resource)

            if len(self.pending_contact):
                self.StartAsyncContact()

            self.logger.info('sent start run '+str(self.runnumber)+' notification to all resources')

            self.startElasticBUWatchdog()
            self.startCompletedChecker()

    def maybeNotifyNewRun(self,resourcename,resourceage,f_ip,override_mask=False):
        if conf.role=='fu':
            self.logger.fatal('RUN:'+str(self.runnumber)+' - this function should *never* have been called when role == fu')
            return

        if self.rawinputdir != None:
            #TODO:check also for EoR file?
            try:
                os.stat(self.rawinputdir)
            except:
                self.logger.warning('Unable to find raw directory of '+str(self.runnumber))
                return None

        for resource in self.online_resource_list:
            if resourcename in resource.cpu and not override_mask:
                if resourcename in self.skip_notification_list:
                    #BU only: update box file IP (data) address and drop from this list in case if disappears later
                    self.logger.info("resource file " + resourcename + " of whitelisted resource has appeared")
                    resource.hostip = f_ip
                    self.skip_notification_list.remove(resourcename)
                    return None
                else:
                    self.logger.error('RUN:'+str(self.runnumber)+' - resource '+str(resource.cpu)+' was already participating in the run. Ignoring until the next run.')
                    return None
            if resourcename in self.rr.boxInfo.machine_blacklist:
                self.logger.info("skipping blacklisted resource "+str(resource.cpu))
                return None
            if self.rr.boxInfo.has_whitelist and resourcename not in self.rr.boxInfo.machine_whitelist:
                self.logger.info("skipping non-whitelisted resource "+str(resource.cpu))
                return None

        current_time = time.time()
        age = current_time - resourceage
        self.logger.info("found resource "+resourcename+" which is "+str(age)+" seconds old")
        if age < 10:
            self.CreateResource([resourcename],f_ip)
            return self.online_resource_list[-1]
        else:
            return None

    def StartOnResource(self, resource,is_locked):
        self.logger.debug("StartOnResource called")
        resource.assigned_run_dir=conf.watch_directory+'/run'+str(self.runnumber).zfill(conf.run_number_padding)
        #support dir rotation in case of static mountpoints
        in_dir = self.bu_base_ram_dirs[self.online_resource_list.index(resource)%len(self.bu_base_ram_dirs)]

        resource.StartNewProcess(self.runnumber,
                                 in_dir,
                                 self.arch,
                                 self.version,
                                 self.menu_path,
                                 int(round((len(resource.cpu)*float(self.resInfo.nthreads)/self.resInfo.nstreams))),
                                 len(resource.cpu),
                                 self.buDataAddr,
                                 self.transferMode,
                                 is_locked)
        self.logger.debug("StartOnResource process started")


    def Stop(self,stop_now=False):
        #used to gracefully stop CMSSW and finish scripts
        with open(os.path.join(self.dirname,"temp_CMSSW_STOP"),'w') as f:
            writedoc = {}
            bu_lumis = []
            try:
                bu_eols_files = [x for x in os.listdir(self.rawinputdir) if x.endswith("_EoLS.jsn")]
                bu_lumis = (sorted([int(x.split('_')[1][2:]) for x in bu_eols_files]))
            except:
                self.logger.error('RUN:'+str(self.runnumber)+" - unable to parse BU EoLS files")
            ls_delay=3
            if not stop_now:
                if len(bu_lumis):
                    self.logger.info('last closed lumisection in ramdisk for run '+str(self.runnumber)+' is '+str(bu_lumis[-1])+', requesting to close at LS '+ str(bu_lumis[-1]+ls_delay))
                    writedoc['lastLS']=bu_lumis[-1]+ls_delay #current+delay
                else:  writedoc['lastLS']=ls_delay
            else:
                writedoc['lastLS']=1
            json.dump(writedoc,f)
        try:
            os.rename(os.path.join(self.dirname,"temp_CMSSW_STOP"),os.path.join(self.dirname,"CMSSW_STOP"))
        except:pass

    def startShutdown(self,killJobs=False,killScripts=False):
        self.runShutdown = threading.Thread(target=self.Shutdown,args=[killJobs,killScripts])
        self.runShutdown.start()

    def joinShutdown(self):
        if self.runShutdown:
            try:
                self.runShutdown.join()
            except:
                return

    def Shutdown(self,killJobs=False,killScripts=False):
        #herod mode sends sigkill to all process, however waits for all scripts to finish
        self.logger.info("run"+str(self.runnumber)+": Shutdown called")
        self.pending_shutdown=False
        self.is_ongoing_run = False

        try:
            self.changeMarkerMaybe(Resource.RunCommon.ABORTED)
        except OSError as ex:
            pass

        time.sleep(.1)
        res_copy = self.online_resource_list[:]
        res_copy_term = []
        try:
            for resource in res_copy: #@SM TODO: combine with join list??
                if resource.processstate==100:
                    res_copy_term.append(resource)
                    try:
                        self.logger.info('terminating process '+str(resource.process.pid)+
                                 ' in state '+str(resource.processstate)+' owning '+str(resource.cpu))

                        if killJobs:resource.process.kill()
                        else:resource.process.terminate()
                    except AttributeError:
                        pass
                    time.sleep(.05)
 
            for resource in res_copy_term: #@SM TODO: combine with join list??
                    if resource.watchdog!=None and resource.watchdog.is_alive():
                        try:
                            resource.join()
                        except:
                            pass
                    try:
                        self.logger.info('process '+str(resource.process.pid)+' terminated')
                    except AttributeError:
                        self.logger.info('terminated process (in another thread)')
                    self.logger.info(' releasing resource(s) '+str(resource.cpu))

            #dereference local copy
            res_copy = []
            res_copy_term = []

            with self.resource_lock:
                q_clear_condition = (not self.checkQuarantinedLimit()) or conf.auto_clear_quarantined or self.shouldClearQuarantined()
                for resource in self.online_resource_list:
                    cleared_q = resource.clearQuarantined(False,restore=q_clear_condition)
                    for cpu in resource.cpu:
                        if cpu not in cleared_q:
                            try:
                                self.resInfo.resmove(self.resInfo.used,self.resInfo.idles,cpu)
                                self.n_used-=1
                            except OSError:
                                #@SM:can happen if it was quarantined
                                self.logger.warning('Unable to find resource '+self.resInfo.used+cpu)
                    resource.process=None

            self.logger.info('completed clearing resource list')

            self.online_resource_list = []
            self.online_resource_list_join = []
            try:
                self.changeMarkerMaybe(Resource.RunCommon.ABORTCOMPLETE)
            except OSError as ex:
                pass
            try:
                if self.anelastic_monitor:
                    if killScripts:
                        self.anelastic_monitor.terminate()
                    self.anelastic_monitor.wait()
            except OSError as ex:
                if ex.errno==3:
                    self.logger.info("anelastic.py for run " + str(self.runnumber) + " is not running")
            except Exception as ex:
                self.logger.exception(ex)
            self.logger.info("anelastic script has been terminated/finished")
            if conf.use_elasticsearch == True:
                if self.elastic_monitor:
                    try:
                        if killScripts:
                            self.elastic_monitor.terminate()
                        #allow monitoring thread to finish, but no more than 30 seconds after others
                        killtimer = threading.Timer(30., self.elastic_monitor.kill)
                        killtimer.start()
                        self.elastic_monitor.wait()
                    except OSError as ex:
                        if ex.errno==3:
                            self.logger.info("elastic.py for run " + str(self.runnumber) + " is not running")
                        else:self.logger.exception(ex)
                    except Exception as ex:
                        self.logger.exception(ex)
                    finally:
                        try:killtimer.cancel()
                        except:pass
                        self.elastic_monitor=None

            if self.waitForEndThread is not None:
                self.waitForEndThread.join()
            self.logger.info("elastic script has been terminated/finished")
        except Exception as ex:
            self.logger.info("exception encountered in shutting down resources")
            self.logger.exception(ex)

        with self.resource_lock:
            try:
               self.runList.remove(self.runnumber)
            except Exception as ex:
                self.logger.exception(ex)

        self.logger.info("removing remaining files...")
        try:
            if conf.delete_run_dir is not None and conf.delete_run_dir:
                shutil.rmtree(conf.watch_directory+'/run'+str(self.runnumber).zfill(conf.run_number_padding))
            os.remove(conf.watch_directory+'/end'+str(self.runnumber).zfill(conf.run_number_padding))
        except:
            pass

        self.logger.info('Shutdown of run '+str(self.runnumber).zfill(conf.run_number_padding)+' completed')

        #activate cloud if planned after shutdown or run stop
        moved_to_cloud=False
        with self.resource_lock:
            if self.state.cloud_mode==True:
                if len(self.runList.getActiveRunNumbers())>=1:
                    self.logger.info("Cloud mode: waiting for runs: " + str(self.runList.getActiveRunNumbers()) + " to finish")
                else:
                    self.logger.info("No active runs. moving all resource files to cloud")
                    #give resources to cloud and bail out
                    self.state.entering_cloud_mode=False
                    #check if cloud mode switch has been aborted in the meantime
                    if self.state.abort_cloud_mode:
                        self.state.abort_cloud_mode=False
                        self.state.cloud_mode=False
                    else:
                        self.resInfo.move_resources_to_cloud()
                        moved_to_cloud=True
        if moved_to_cloud:
            self.StartCloud()


    def StartCloud(self):
        result = self.state.ignite_cloud()
        c_status = self.state.cloud_status()
        if c_status == 0:
            self.logger.warning("igniter status : cloud is NOT active (hltd will remain in cloud-on state until it is included back in HLT)")
        elif c_status == 1:
            self.logger.info("igniter status : cloud has been activated")
        else:
            self.logger.warning("cloud is in error state:" + str(c_status))


    def ShutdownBU(self):
        self.is_ongoing_run = False
        self.stopAsyncContact()
        #TODO: kill async checker thread too
        try:
            if self.elastic_monitor:
                #first check if process is alive
                if self.elastic_monitor.poll() is None:
                    self.elastic_monitor.terminate()
                    time.sleep(.1)
        except Exception as ex:
            self.logger.info("exception encountered in shutting down elasticbu.py: " + str(ex))
            #self.logger.exception(ex)

        #should also trigger destructor of the Run

        with self.resource_lock:
            try:
                self.runList.remove(self.runnumber)
            except Exception as ex:
                self.logger.exception(ex)

        self.logger.info('Shutdown of run '+str(self.runnumber).zfill(conf.run_number_padding)+' on BU completed')

    def StartAsyncContact(self):
        self.logger.info("Starting periodic notify attempt thread for " + str(len(self.pending_contact)) + " resources")
        try:
            self.asyncContactThread = threading.Thread(target=self.AsyncContact)
            self.asyncContactThread.start()
        except Exception as ex:
            self.logger.info("exception encountered in starting async contact thread")
            self.logger.exception(ex)

    def AsyncContact(self):
        self.logger.info("Async contact thread")
        try:
          self.threadEventContact.wait(60)
          while not self.stopThreads and len(self.pending_contact):
            for res in self.pending_contact[:]:
                if res.ok:
                    self.pending_contact.remove(res)
                    continue
                try:
                    self.logger.info('start run '+str(self.runnumber)+' on resources '+str(res.cpu)+" (by check)")
                    res.NotifyNewRun(self.runnumber,self.send_bu,warnonly=True)
                    if res.ok:
                      self.pending_contact.remove(res)
                    self.logger.info("Remaining resources to contact: " + str([x.cpu[0] for x in self.pending_contact]))
                except Exception as ex:
                    self.logger.info('RUN:'+str(self.runnumber)+' - exception in acquiring whitelisted resource (periodic check) '+str(res.cpu)+':'+str(ex))
            #run check periodically
            self.threadEventContact.wait(300)
        except:
          self.logger.warning("Exception in AsyncContact " + str(ex))


    def stopAsyncContact(self):
        if conf.role != 'bu': return
        self.pending_contact = []
        self.threadEventContact.set()
        try:
            if self.asyncContactThread:
                self.asyncContactThread.join()
        except:
            pass

        self.asyncContactThread = None


    def StartWaitForEnd(self):
        self.is_ongoing_run = False
        self.changeMarkerMaybe(Resource.RunCommon.STOPPING)
        try:
            self.waitForEndThread = threading.Thread(target=self.WaitForEnd)
            self.waitForEndThread.start()
        except Exception as ex:
            self.logger.info("exception encountered in starting run end thread")
            self.logger.info(ex)

    def WaitForEnd(self):
        self.logger.info("wait for end thread!")
        self.stopAsyncContact()
        try:
            for resource in self.online_resource_list_join:
                if resource.processstate is not None:
                    if resource.process is not None and resource.process.pid is not None: ppid = resource.process.pid
                    else: ppid="None"
                    self.logger.info('waiting for process '+str(ppid)+
                                 ' in state '+str(resource.processstate) +
                                 ' to complete ')
                    try:
                        while True:
                            resource.join(timeout=300)
                            if not resource.isAlive():
                                break
                            with self.resource_lock:
                                #retry again with lock acquired
                                if not resource.isAlive():
                                    break
                                self.logger.warning("timeout waiting for run to end (5 min) pid: "+str(ppid)+" . retrying join...")
                                #check if cloud is aborting and finish action if needed
                                if self.state.cloud_mode and self.state.abort_cloud_mode:
                                    self.logger.warning("detected cloud abort signal while waiting for run end, aborting cloud switch and setting masked resource flag until the next run")
                                    self.state.abort_cloud_mode=False
                                    self.state.masked_resources=True
                                    self.state.cloud_mode=False

                        self.logger.info('process '+str(resource.process.pid)+' completed')
                    except Exception as ex:
                        self.logger.warning(str(ex))
                resource.clearQuarantined()
                resource.process=None

            self.online_resource_list_join = []
            self.online_resource_list = []

            if conf.role == 'fu':
                self.logger.info('writing complete file')
                self.changeMarkerMaybe(Resource.RunCommon.COMPLETE)
                try:
                    os.remove(conf.watch_directory+'/end'+str(self.runnumber).zfill(conf.run_number_padding))
                except:pass
                try:
                    if not conf.dqm_machine:
                        self.anelastic_monitor.wait()
                except OSError as ex:
                    if "No child processes" not in str(ex):
                        self.logger.info("Exception encountered in waiting for termination of anelastic:" +str(ex))
                except AttributeError as ex:
                    self.logger.info("Exception encountered in waiting for termination of anelastic:" +str(ex))
                self.anelastic_monitor = None

            if conf.use_elasticsearch == True:
                try:
                    self.elastic_monitor.wait()
                except OSError as ex:
                    if "No child processes" not in str(ex):
                        self.logger.info("Exception encountered in waiting for termination of elastic:" +str(ex))
                except AttributeError as ex:
                    self.logger.info("Exception encountered in waiting for termination of elastic:" +str(ex))
                self.elastic_monitor = None
            if conf.delete_run_dir is not None and conf.delete_run_dir == True:
                try:
                    shutil.rmtree(self.dirname)
                except Exception as ex:
                    self.logger.exception(ex)

            #todo:clear this external thread
            moved_to_cloud=False
            with self.resource_lock:
                self.logger.info("active runs.."+str(self.runList.getActiveRunNumbers()))
                try:
                    self.runList.remove(self.runnumber)
                except Exception as ex:
                    self.logger.exception(ex)
                self.logger.info("new active runs.."+str(self.runList.getActiveRunNumbers()))

                if self.state.cloud_mode==True:
                    if len(self.runList.getActiveRunNumbers())>=1:
                        self.logger.info("Cloud mode: waiting for runs: " + str(self.runList.getActiveRunNumbers()) + " to finish")
                    else:
                        self.logger.info("No active runs. moving all resource files to cloud")
                        #give resources to cloud and bail out
                        self.state.entering_cloud_mode=False
                        #check if cloud mode switch has been aborted in the meantime
                        if self.state.abort_cloud_mode:
                            self.state.abort_cloud_mode=False
                            self.state.cloud_mode=False
                            return

                        self.resInfo.move_resources_to_cloud()
                        moved_to_cloud=True
            if moved_to_cloud:
                self.StartCloud()

        except Exception as ex:
            self.logger.error('RUN:'+str(self.runnumber)+" - exception encountered in ending run")
            self.logger.exception(ex)

    def changeMarkerMaybe(self,marker):
        current = [x for x in os.listdir(self.dirname) if x in Resource.RunCommon.VALID_MARKERS]
        if (len(current)==1 and current[0] != marker) or len(current)==0:
            if len(current)==1: os.remove(self.dirname+'/'+current[0])
            fp = open(self.dirname+'/'+marker,'w+')
            fp.close()
        else:
            self.logger.error('RUN:'+str(self.runnumber)+" - there are more than one markers for run ")
            return

    def checkQuarantinedLimit(self):
        allQuarantined=True
        for r in self.online_resource_list:
            try:
                if r.watchdog.quarantined==False or r.processstate==100:allQuarantined=False
            except Exception as ex:
                self.logger.warning(str(ex))
                allQuarantined=False
        if allQuarantined==True:
            return True
        else:
            return False

    def startAnelasticWatchdog(self):
        try:
            self.anelasticWatchdog = threading.Thread(target=self.runAnelasticWatchdog)
            self.anelasticWatchdog.start()
        except Exception as ex:
            self.logger.info("exception encountered in starting anelastic watchdog thread")
            self.logger.info(ex)

    def runAnelasticWatchdog(self):
        try:
            self.anelastic_monitor.wait()
            if self.is_ongoing_run == True:
                #abort the run
                self.anelasticWatchdog=None
                self.logger.warning("Premature end of anelastic.py for run "+str(self.runnumber))
                #self.logger.warning("Setting resources released flag to masked until the next run on this machine")
                #self.state.masked_resources=True #set this flag to prevent events being built until the next run
                self.Shutdown(killJobs=True,killScripts=True)
        except:
            pass
        self.anelastic_monitor=None

    def startElasticBUWatchdog(self):
        try:
            self.elasticBUWatchdog = threading.Thread(target=self.runElasticBUWatchdog)
            self.elasticBUWatchdog.start()
        except Exception as ex:
            self.logger.info("exception encountered in starting elasticbu watchdog thread")
            self.logger.info(ex)

    def runElasticBUWatchdog(self):
        try:
            self.elastic_monitor.wait()
        except:
            pass
        self.elastic_monitor=None

    def startCompletedChecker(self):

        try:
            self.logger.info('start checking completion of run '+str(self.runnumber))
            self.completedChecker = threading.Thread(target=self.runCompletedChecker)
            self.completedChecker.start()
        except Exception as ex:
            self.logger.error('RUN:'+str(self.runnumber)+' - failure to start run completion checker')
            self.logger.exception(ex)

    def runCompletedChecker(self):

        rundirstr = 'run'+ str(self.runnumber).zfill(conf.run_number_padding)
        rundirCheckPath = os.path.join(conf.watch_directory, rundirstr)
        eorCheckPath = os.path.join(rundirCheckPath,rundirstr + '_ls0000_EoR.jsn')

        self.threadEvent.wait(10)
        while self.stopThreads == False:
            self.threadEvent.wait(5)
            if os.path.exists(eorCheckPath) or os.path.exists(rundirCheckPath)==False:
                self.stopAsyncContact()
                self.logger.info("Completed checker: detected end of run "+str(self.runnumber))
                break

        while self.stopThreads == False:
            self.threadEvent.wait(5)
            success, runFound = self.rr.checkNotifiedBoxes(self.runnumber)
            if success and runFound==False:
                with self.resource_lock:
                    try:
                        self.runList.remove(self.runnumber)
                    except Exception as ex:
                        self.logger.exception(ex)
                self.stopAsyncContact()
                self.logger.info("Completed checker: end of processing of run "+str(self.runnumber))
                break

    def createEmptyEoRMaybe(self):

        #this is used to notify elasticBU to fill the end time before it is terminated
        rundirstr = 'run'+ str(self.runnumber).zfill(conf.run_number_padding)
        rundirCheckPath = os.path.join(conf.watch_directory, rundirstr)
        eorCheckPath = os.path.join(rundirCheckPath,rundirstr + '_ls0000_EoR.jsn')
        try:
            os.stat(eorCheckPath)
        except:
            self.logger.info('creating empty EoR file in run directory '+rundirCheckPath)
            try:
                with open(eorCheckPath,'w') as fi:
                    pass
                time.sleep(.5)
            except Exception as ex:
                self.logger.exception(ex)

    def shouldClearQuarantined(self):

        return self.clear_quarantined_count != 0 and self.not_clear_quarantined_count == 0


    def getHltInfoParameters(self):
        try:
            with open(self.hltinfofile_path,'r') as fp:
                hltInfo = json.load(fp)

                if isinstance(hltInfo['isGlobalRun'],str):
                    self.state.isGlobalRun = True if hltInfo['isGlobalRun']=="1" else False
                else:
                    self.state.isGlobalRun = hltInfo['isGlobalRun']

                try:
                    self.state.daqSystem = hltInfo['daqSystem']
                except:
                    pass

                self.state.daqInstance = hltInfo['daqInstance']
                self.state.fuGroup = hltInfo['fuGroup']
                self.logger.info("Run " + str(self.runnumber) + " DAQ system " + 
                                 self.state.daqSystem + " instance " +
                                 self.state.daqInstance + " " + self.state.fuGroup)
                return True
        except ValueError as ex:
            self.logger.exception(ex)
        except Exception as ex:
        # FileNotFoundError as ex:
            self.logger.warning(str(ex))
        return False



