import os
import signal
import time
import threading
try:
  from httplib import HTTPConnection
except:
  from http.client import HTTPConnection
import shutil
import demote
import prctl
from signal import SIGKILL
import subprocess
import logging
import socket
import pwd

import Run
from HLTDCommon import restartLogCollector,dqm_globalrun_filepattern
from MountManager import find_nfs_mountpoints,find_nfs_mount_addr
from inotifywrapper import InotifyWrapper

this_machine=os.uname()[1]
this_machine_short=this_machine.split('.')[0]

def preexec_function():
    dem = demote.demote(conf.user)
    dem()
    prctl.set_pdeathsig(SIGKILL)
    #    os.setpgrp()

def tryremove(fpath):
    try:os.remove(fpath)
    except:pass

class RunRanger:

    def __init__(self,instance,confClass,stateInfo,resInfo,runList,resourceRanger,mountMgr,sysMon,logCollector,nsslock,resource_lock):
        self.inotifyWrapper = InotifyWrapper(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.instance = instance
        self.state = stateInfo
        self.resInfo = resInfo
        self.runList = runList
        self.rr = resourceRanger
        self.mm = mountMgr
        self.sm = sysMon
        self.logCollector = logCollector
        self.nsslock = nsslock
        self.resource_lock = resource_lock
        self.bu_emulator = None
        self.pw_record = pwd.getpwnam(confClass.user)
        global conf
        conf = confClass

    def register_inotify_path(self,path,mask):
        self.inotifyWrapper.registerPath(path,mask)

    def start_inotify(self):
        self.inotifyWrapper.start()

    def stop_inotify(self):
        self.inotifyWrapper.stop()
        self.inotifyWrapper.join()
        self.logger.info("Inotify wrapper shutdown done")

    def process_IN_CREATE(self, event):
        fullpath = event.fullpath
        self.logger.info('event '+fullpath)
        dirname=fullpath[fullpath.rfind("/")+1:]
        suffix=''
        s_pos = dirname.find('_')
        if s_pos >=0:
          suffix = dirname[s_pos+1:]
          dirname = dirname[:s_pos]

        #detect if number is appended to the end of the command
        numChar = -1
        for i,c in enumerate(dirname):
          if c.isdigit() and numChar==-1:
            numChar=i
          elif not c.isdigit() and numChar!=-1:
            numChar=-1
            break

        prefix = dirname if numChar==-1 else dirname[:numChar]
        dirnum = -1 if numChar==-1 else int(dirname[numChar:])

        self.logger.info('new filename '+dirname)

        self.acqs = None


        try:
          if prefix in ['run']:              #BU,FU
            self.newRunCmd(dirname,dirnum,suffix,fullpath)

          elif prefix in ['end']:            #FU
            self.endRunCmd(dirnum,fullpath)

          elif prefix in ['quarantined']:    #FU
            tryremove(dirname)
            if conf.role == 'fu':
              self.quarantinedCmd(dirnum)

          elif prefix in ['stop']:           #FU
            if conf.role == 'fu':
              self.stopCmd(dirname)
            tryremove(fullpath)
 
          elif prefix in ['exclude']:        #FU
            if conf.role == 'fu':
              self.excludeCmd(dirname)
            tryremove(fullpath)
  
          elif prefix in ['include']:        #FU
            if conf.role == 'fu':
              self.includeCmd(dirname,fullpath)
            tryremove(fullpath)
 
          elif prefix in ['resourceupdate']: #FU
            self.resourceUpdateCmd()
            tryremove(dirname)

          elif prefix in ['removebox']: #FU
            self.removeBoxCmd(suffix)

          elif prefix in ['restart']:        #BU,FU
            self.logger.info('restart event')
            if conf.role=='bu':
              self.restartBUCmd()
            #some time to allow cgi return
            time.sleep(1)
            tryremove(fullpath)

            pr = subprocess.Popen(["/opt/hltd/scripts/restart.py"],close_fds=True)
            self.logger.info('restart imminent, waiting to die and raise from the ashes once again')

          elif prefix in ['herod','tsunami','brutus']: #FU,BU
              if conf.role == 'bu':
                  self.cleanupBUCmd(dirname,dirnum)
                  tryremove(fullpath)
                  if prefix == 'tsunami':
                      self.cleanDisksCmd(dirnum,clrRamdisk=True,clrOutput=True)
              elif conf.role == 'fu':
                  tryremove(fullpath)
                  self.cleanupFUCmd(prefix,dirnum,suffix)

          elif prefix in ['cleanoutput']: #BU
              tryremove(fullpath)
              if conf.role == 'bu':
                  self.cleanDisksCmd(dirnum,clrRamdisk=False,clrOutput=True)

          elif prefix in ['cleanramdisk']: #BU
              tryremove(fullpath)
              if conf.role == 'bu':
                  self.cleanDisksCmd(dirnum,clrRamdisk=True,clrOutput=False)

          elif prefix in ['suspend']: #FU (BU:warning)
            if conf.role == 'fu':
              self.suspendCmd(dirnum,fullpath,suffix.split('_'))
            else:
              self.logger.warning("unable to suspend on " + conf.role)
              tryremove(fullpath)
 
          elif prefix in ['logrestart']:     #BU,FU
            #hook to restart logcollector process manually
            restartLogCollector(conf,self.logger,self.logCollector,self.instance)
            tryremove(fullpath)

          elif prefix in ['harakiri']: #FU (used?)
              tryremove(fullpath)
              if conf.role == 'fu':
                  self.harakiriCmd()

          elif prefix=="cgi-bin":
            pass
          elif dirname.startswith("switchbu_"):
            tryremove(fullpath)

          else:
            self.logger.warning("unrecognized command "+fullpath)
            tryremove(fullpath)
        except Exception as ex:
          self.logger.error("Encountered exception in RunRanger during handling of "+ fullpath)
          self.logger.exception(ex)

        self.logger.debug("completed handling of event "+fullpath)

    def process_default(self, event):
        self.logger.info('event '+event.fullpath+' type '+str(event.mask))
        filename=event.fullpath[event.fullpath.rfind("/")+1:]


    def newRunCmd(self,dirname,rn,bu_mount_suffix,fullpath):
        if os.path.islink(fullpath):
            self.logger.info('directory ' + fullpath + ' is link. Ignoring this run')
            return
        if not os.path.isdir(fullpath):
            self.logger.info(fullpath +' is a file. A directory is needed to start a run.')
            return

        #check and fix directory ownership if not created as correct user and group (in case of manual creation)
        if conf.role=='fu' and not conf.dqm_machine:

            if bu_mount_suffix:
                #rename to non-suffix version
                fullpath_old = fullpath
                fullpath = fullpath[:fullpath.rfind('/')+1]+dirname
                os.rename(fullpath_old,fullpath)
                #signal to monitoring and heartbeat handler to switch to a different BU mount point (dynamic)
                #NOTE:this could block in case of network issue
                self.sm.notifyMaybeChangeBU(bu_mount_suffix)

            try:
                stat_res = os.stat(fullpath)
                if self.pw_record.pw_uid!=stat_res.st_uid or self.pw_record.pw_gid!=stat_res.st_gid:
                  self.logger.info("fixing owner of the run directory")
                  os.chown(fullpath,self.pw_record.pw_uid,self.pw_record.pw_gid) 
                os.chmod(fullpath,0o777)
            except Exception as ex:
                self.logger.warning("exception checking run directory ownership and mode: "+str(ex))

        if rn>0:
            # the dqm BU processes a run if the "global run file" is not mandatory or if the run is a global run
            is_global_run = os.path.exists(fullpath[:fullpath.rfind("/")+1] + dqm_globalrun_filepattern.format(str(rn).zfill(conf.run_number_padding)))
            dqm_processing_criterion = (not conf.dqm_globallock) or (conf.role != 'bu') or  (is_global_run)

            if (not conf.dqm_machine) or dqm_processing_criterion:
                try:
                        self.logger.info('new run '+str(rn))
                        #terminate quarantined runs
                        for run in self.runList.getQuarantinedRuns():
                            #run shutdown waiting for scripts to finish
                            run.startShutdown(True,False)
                            time.sleep(.1)

                        #self.state.resources_blocked_flag=False
                        if self.state.cloud_mode==True:
                            self.logger.info("received new run notification in CLOUD mode. Ignoring new run.")
                            os.rmdir(fullpath)
                            return
                        self.state.masked_resources=False #clear this flag for run that was stopped manually
                        bu_dir_base_vec = [None]
                        bu_out_dir_base = None
                        bu_dir = None
                        if conf.role == 'fu':
                            if self.mm and not bu_mount_suffix:
                              bu_dir_base_vec = self.mm.bu_disk_list_ramdisk_instance
                              bu_out_dir_base = self.mm.bu_disk_list_output_instance[0]
                            else:
                              if not bu_mount_suffix:
                                self.logger.error("error, no BU mount suffix present (dynamic mounting mode)")
                                return
                              #set dynamic mountpoint to start the run in
                              bu_dir_base_vec = [os.path.join(conf.bu_base_dir_autofs,bu_mount_suffix + '_' + conf.ramdisk_subdirectory)]
                              bu_out_dir_base = os.path.join(conf.bu_base_dir_autofs,bu_mount_suffix + '_' + conf.output_subdirectory)

                            bu_dir = os.path.join(bu_dir_base_vec[0],dirname)
                            try:
                                os.symlink(bu_dir+'/jsd',fullpath+'/jsd')
                            except:
                                if not conf.dqm_machine:
                                    self.logger.warning('jsd directory symlink error, continuing without creating link')

                        #check if this run is a duplicate
                        if self.runList.getRun(rn)!=None:
                            raise Exception("Attempting to create duplicate run "+str(rn))

                        # in case of a DQM machines create an EoR file
                        if conf.dqm_machine and conf.role == 'bu':
                            for run in self.runList.getOngoingRuns():
                                EoR_file_name = run.dirname + '/' + 'run' + str(run.runnumber).zfill(conf.run_number_padding) + '_ls0000_EoR.jsn'
                                if run.is_ongoing_run and not os.path.exists(EoR_file_name):
                                    # create an EoR file that will trigger all the running jobs to exit nicely
                                    open(EoR_file_name, 'w').close()

                        if not len(self.runList.getActiveRuns()) and conf.role == 'fu':
                          if self.state.os_cpuconfig_change:
                            with self.state.lock:
                              tmp_os_cpuconfig_change = self.state.os_cpuconfig_change
                              self.state.os_cpuconfig_change=0
                            with self.resource_lock:
                              tmp_change = self.resInfo.updateIdles(tmp_os_cpuconfig_change,checkLast=False)
                              self.state.os_cpuconfig_change=tmp_change

                        run = Run.Run(rn,fullpath,bu_dir_base_vec,bu_dir,bu_out_dir_base,self.instance,conf,self.state,self.resInfo,self.runList,self.rr,self.nsslock,self.resource_lock)
                        if not run.inputdir_exists and conf.role=='fu':
                            self.logger.info('skipping '+ fullpath + ' with raw input directory missing')
                            shutil.rmtree(fullpath)
                            del run
                            return

                        with self.resource_lock:
                          self.runList.add(run)
                          try:
                              if conf.role=='fu' and not self.state.entering_cloud_mode and not self.resInfo.has_active_resources():
                                  self.logger.error("RUN:"+str(run.runnumber)+' - trying to start a run without any available resources (all are QUARANTINED) - this requires manual intervention !')
                          except Exception as ex:
                              self.logger.exception(ex)

                          if run.AcquireResources(mode='greedy'):
                              run.CheckTemplate()
                              run.Start()
                              acquire_success = True
                          else:
                              #BU mode: failed to get blacklist
                              self.runList.remove(rn)
                              acquire_success = False
                        #end of locked section

                        if not acquire_success:
                            try:del run
                            except:pass
                            return

                        if conf.role == 'bu' and conf.instance != 'main':
                            self.logger.info('creating run symlink in main ramdisk directory')
                            main_ramdisk = os.path.dirname(os.path.normpath(conf.watch_directory))
                            os.symlink(fullpath,os.path.join(main_ramdisk,os.path.basename(fullpath)))
                except OSError as ex:
                        self.logger.error("RUN:"+str(rn)+" - exception in new run handler: "+str(ex)+" / "+ex.filename)
                        self.logger.exception(ex)
                except Exception as ex:
                        self.logger.error("RUN:"+str(rn)+" - RunRanger: unexpected exception encountered in forking hlt slave")
                        self.logger.exception(ex)


    def endRunCmd(self,rn,fullpath):
            if rn>0:
                    try:
                        endingRun = self.runList.getRun(rn)
                        if endingRun==None:
                            self.logger.warning('request to end run '+str(rn)
                                          +' which does not exist')
                            os.remove(fullpath)
                            return
                        else:
                            self.logger.info('end run '+str(rn))
                            #remove from runList to prevent intermittent restarts
                            #lock used to fix a race condition when core files are being moved around
                            endingRun.is_ongoing_run=False
                            time.sleep(.1)
                            if conf.role == 'fu':
                                endingRun.StartWaitForEnd()
                            if self.bu_emulator and self.bu_emulator.runnumber != None:
                                self.bu_emulator.stop()
                            #self.logger.info('run '+str(rn)+' removing end-of-run marker')
                            #os.remove(fullpath)

                    except Exception as ex:
                        self.logger.info("exception encountered when waiting hlt run to end")
                        self.logger.info(ex)
            else:
                    self.logger.error('request to end run '+str(rn)
                                  +' which is an invalid run number - this should '
                                  +'*never* happen')


    def removeBoxCmd(self,suffix):
        self.logger.info("removing box file from "+suffix)
        self.sm.notifyMaybeRemoveBUMaybe(suffix)
        self.logger.info("remove box file done")

    def cleanupFUCmd(self,prefix,rn,suffix):

        kill_all_runs = True if rn<=0 else False

        self.logger.info("killing all CMSSW child processes")
        #clear ongoing flags to avoid latest run picking up released resources (only if not killing a specific run)
        if kill_all_runs:
            self.runList.clearOngoingRunFlags()

                #wait 5 seconds for BU to finish with the command (until ramdisk marker is deleted), otherwise do cleanup
        timeLeft=5
        while timeLeft>0:
                  try:
                      bu_files = [] #no files in case of failure
                      if suffix:
                          bu_dir_autofs = os.path.join(conf.bu_base_dir_autofs,suffix+'_'+conf.ramdisk_subdirectory)
                          try:
                              os.stat(bu_dir_autofs)
                              bu_files = os.listdir(bu_dir_autofs)
                          except OSError:
                              bu_dir_static = os.path.join(conf.bu_base_dir+'0',conf.ramdisk_subdirectory)
                              static_addr = find_nfs_mount_addr(bu_dir_static)
                              if static_addr and static_addr.split('.')[0]==suffix:
                                  bu_files = os.listdir(bu_dir_static)
                  except Exception as ex: #catch-all
                      self.logger.exception(ex)
                      break
                  found_marker=False
                  for bu_file in bu_files:
                    if bu_file.startswith('herod') or bu_file.startswith('tsunami') or bu_file.startswith('brutus'):
                      found_marker=True
                  if not found_marker:
                    self.logger.info('no BU markers left, proceeding with termination')
                    break
                  self.logger.info('waiting for BU to finish run termination')
                  timeLeft-=1
                  time.sleep(1)

        sh_kill_scripts=False if prefix=='brutus' else True

        for run in self.runList.getActiveRuns():
                  if kill_all_runs or run.runnumber==rn or run.checkQuarantinedLimit():
                    run.Shutdown(True,sh_kill_scripts)

        time.sleep(.2)
        #clear all quarantined cores
        for cpu in self.resInfo.q_list:
                    try:
                        self.logger.info('Clearing quarantined resource '+cpu)
                        self.resInfo.resmove(self.resInfo.quarantined,self.resInfo.idles,cpu)
                    except:
                        self.logger.info('Quarantined resource was already cleared: '+cpu)
        self.resInfo.q_list=[]
        self.logger.info("cleanup done")

    def cleanupBUCmd(self,dirname,rn):
        kill_all_runs = True if rn<=0 else False

        #contact any FU that appears alive
        boxdir = conf.resource_base +'/boxes/'
        try:
                    dirlist = os.listdir(boxdir)
                    current_time = time.time()
                    self.logger.info("sending "+dirname+" to child FUs")
                    herod_threads = []
                    for name in dirlist:
                        if name == this_machine:continue
                        age = current_time - os.path.getmtime(boxdir+name)
                        self.logger.info('found box '+name+' with keepalive age '+str(age))
                        if age < 300:
                            self.logger.info('contacting '+str(name))

                            def notifyHerod(hname):

                                host_short = hname.split('.')[0]
                                #get hosts from cached ip if possible to avoid hammering DNS
                                try:
                                    hostip = self.rr.boxInfo.FUMap[host_short][0]['ip']
                                except:
                                    self.logger.info(str(host_short) + ' not in FUMap')
                                    hostip=hname

                                attemptsLeft=4
                                while attemptsLeft>0:
                                    attemptsLeft-=1
                                    try:
                                        connection = HTTPConnection(hostip, conf.cgi_port - conf.cgi_instance_port_offset,timeout=10)
                                        time.sleep(0.2)
                                        connection.request("GET",'cgi-bin/herod_cgi.py?command='+str(dirname)+'&buname='+this_machine_short)
                                        time.sleep(0.3)
                                        response = connection.getresponse()
                                        self.logger.info("sent "+ dirname +" to child FUs")
                                        break
                                    except Exception as ex:
                                        self.logger.error("exception encountered in contacting resource "+str(hostip))
                                        self.logger.exception(ex)
                                        time.sleep(.3)
                            try:
                                herodThread = threading.Thread(target=notifyHerod,args=[name])
                                herodThread.start()
                                herod_threads.append(herodThread)
                            except Exception as ex:
                                self.logger.exception(ex)

                    #join herod before returning
                    for herodThread in herod_threads:
                      herodThread.join()

        except Exception as ex:
                    self.logger.error("exception encountered in contacting resources")
                    self.logger.info(ex)

        #cleanup after contacting FUs. FUs will however still wait a few seconds for tsunami/herod/brutus file to be deleted
        time.sleep(.5)
        for run in self.runList.getActiveRuns():
                    if kill_all_runs or run.runnumber==rn:
                      run.createEmptyEoRMaybe()
                      run.ShutdownBU()
        time.sleep(.5)



    def cleanDisksCmd(self,rn,clrRamdisk,clrOutput):

        if rn<=0:
            self.logger.info('cleaning output (all run data)')
            self.logger.info('cleaning ramdisk' + str(clrRamdisk) + " output:" + str(clrOutput) +  ' for all runs')
            self.mm.cleanup_bu_disks(None,clrRamdisk,clrOutput)
        else:
            try:
                self.logger.info('cleaning ramdisk' + str(clrRamdisk) + " output:" + str(clrOutput) +  '(only for run '+str(rn)+')')
                self.mm.cleanup_bu_disks(rn,clrRamdisk,clrOutput)
            except Exception as ex:
                self.logger.error('Could not clean data: '+ str(ex))


    def harakiriCmd(self):

            pid=os.getpid()
            self.logger.info('asked to commit seppuku:'+str(pid))
            try:
                self.logger.info('sending signal '+str(SIGKILL)+' to myself:'+str(pid))
                retval = os.kill(pid, SIGKILL)
                self.logger.info('sent SIGINT to myself:'+str(pid))
                self.logger.info('got return '+str(retval)+'waiting to die...and hope for the best')
            except Exception as ex:
                self.logger.error("exception in committing harakiri - the blade is not sharp enough...")
                self.logger.error(ex)


    def quarantinedCmd(self,rn):

            if rn>0:
                    try:
                        run = self.runList.getRun(rn)
                        if run.checkQuarantinedLimit():
                            if self.runList.isLatestRun(run):
                                self.logger.info('reached quarantined limit - pending Shutdown for run:'+str(rn))
                                run.pending_shutdown=True
                            else:
                                self.logger.info('reached quarantined limit - initiating Shutdown for run:'+str(rn))
                                run.startShutdown(True,False)
                    except Exception as ex:
                        self.logger.exception(ex)


    def suspendCmd(self,dirnum,fullpath,suffix_arr):
            #command received on FU
            self.logger.info('suspend mountpoints initiated')
            self.state.suspended=True
            replyport = dirnum if dirnum!=-1 else 0

            #terminate all ongoing runs
            self.runList.clearOngoingRunFlags()
            for run in self.runList.getActiveRuns():
                run.Shutdown(True,True)

            time.sleep(.5)
            #local request used in case of stale file handle

            bu_name_ip = suffix_arr[0]
            umount_success = True

            def do_umount():
                nonlocal umount_success
                umount_success = self.mm.cleanup_mountpoints(self.nsslock,remount=False) if self.mm else umount_success
                self.logger.warning("running suspend (check) for dynamic mounts")
                bu_name_short = suffix_arr[1] if len(suffix_arr)>1 else ""
                #run this either for BU which asked for suspend, or for any local mountpoint if command is initiated locally
                if len(suffix_arr)>1 or replyport==0:
                  found_mps = find_nfs_mountpoints([os.path.join(conf.bu_base_dir_autofs,bu_name_short + '_' + conf.ramdisk_subdirectory),
                                                    os.path.join(conf.bu_base_dir_autofs,bu_name_short + '_' + conf.output_subdirectory)])
                  for found in found_mps:
                    #will force unmount in case of a process keeping mount busy
                    self.logger.warning("running umount for "+found)
                    try:
                      subprocess.check_call(['umount','-f',found])
                      #subprocess.check_call(['umount','-l',found]) #could also use lazy unmount
                    except Exception as ex:
                      self.logger.error(str(ex))
                      umount_success=False

            def do_mount():
                nonlocal umount_success
                umount_sucess = umount_success and (self.mm.cleanup_mountpoints(self.nsslock) if self.mm else True)
                self.logger.info("Remount for replyport="+str(replyport) + " host=" + bu_name_ip + " is performed.")
                try:os.remove(fullpath)
                except:pass
                self.state.suspended=False

            do_umount()

            if replyport==0 or len(suffix_arr)==0:
              if len(suffix_arr)==0:
                self.logger.error("no BU reply address provided!")
              do_mount()
              return


            if umount_success==False:
                time.sleep(1)
                self.logger.error("Suspend initiated from BU failed, trying again...")
                #notifying itself again
                try:os.remove(fullpath)
                except:pass
                fp = open(fullpath,"w+")
                fp.close()
                return

            #first report to BU that umount was done
            try:
                connection = HTTPConnection(bu_name_ip, replyport+20,timeout=5)
                connection.request("GET",'cgi-bin/report_suspend_cgi.py?host='+this_machine)
                response = connection.getresponse()
            except Exception as ex:
                self.logger.error("Unable to report suspend state to BU "+str(bu_name_ip)+':'+str(replyport+20))
                self.logger.exception(ex)
                #BU could already be down, continue to a polling loop
                time.sleep(1)

            #loop while BU is not reachable
            while True:
                try:
                    self.logger.info('checking if BU hltd is available...')
                    connection = HTTPConnection(bu_name_ip, replyport,timeout=5)
                    connection.request("GET",'cgi-bin/getcwd_cgi.py')
                    response = connection.getresponse()
                    self.logger.info('BU hltd is running !...')
                    #if we got here, the service is back up
                    break
                except Exception as ex:
                    try:
                        self.logger.info('Failed to contact BU hltd service: ' + str(ex.args[0]) +" "+ str(ex.args[1]))
                    except:
                        self.logger.info('Failed to contact BU hltd service '+str(ex))
                    time.sleep(5)

            #mount again when BU is back
            do_mount()


    def stopCmd(self,dirname):

            self.logger.info("Stop command invoked: "+ dirname)

            #lock to get consistent state
            with self.resource_lock:
              self.state.disabled_resource_allocation=True
              q_list = self.runList.getQuarantinedRuns()
              a_list = self.runList.getActiveRuns()
              ongoing_rnlist = [r.runnumber for r in self.runList.getOngoingRuns()]
            #end of locked section

            self.logger.info('active runs:'+str([r.runnumber for r in a_list]) + ' quarantined runs:' + str([r.runnumber for r in q_list]))

            nlen = len('stopnow') if dirname.startswith('stopnow') else len('stop')
            stop_now_cmd = True if dirname.startswith('stopnow') else False
            stop_all_runs = True if nlen==len(dirname) else False

            if not stop_all_runs:
              stop_suffix = dirname[nlen:]
              try:
                  if stop_suffix.isdigit():
                    rn = int(stop_suffix)
                    found=False
                    for run in q_list:
                      if run.runnumber==rn:
                        found=True
                        if len(ongoing_rnlist):
                          #not the only run
                          self.state.masked_resources=True
                        run.Shutdown(True,False)
                        break
                    if not found:
                      for run in a_list:
                        if run.runnumber==rn and not run.pending_shutdown:
                          found=True
                          ongoing_rnlist.remove(rn)
                          if len(ongoing_rnlist)==0:
                            #mask if this is the only run. otherwise another run will start on released resources
                            self.state.masked_resources=True
                          if len(run.online_resource_list)==0:
                            run.Shutdown(True,False)
                          else:
                            run.Stop(stop_now=stop_now_cmd)
                          break
                    if found:time.sleep(.1)
                  else:
                    self.logger.error("can not parse run number suffix from "+dirname+ ". Aborting command")
              except Exception as exp:
                  self.logger.error("Exception parsing run number suffix from " +dirname+". Aborting command")
                  self.logger.exception(exp)

            else:
              self.logger.info('setting masked flag')
              #mask released resources from BU until next run is started
              self.state.masked_resources=True

              #this disables any already started run to pick up released resources
              self.runList.clearOngoingRunFlags()
              #shut down any quarantined runs
              try:
                for run in q_list:
                    run.Shutdown(True,False)
                for run in a_list:
                    if not run.pending_shutdown:
                        if len(run.online_resource_list)==0:
                            run.Shutdown(True,False)
                        else:
                            run.Stop(stop_now=stop_now_cmd)
                time.sleep(.1)
              except Exception as ex:
                self.logger.fatal("Unable to stop run(s)")
                self.logger.exception(ex)

            self.state.disabled_resource_allocation=False


    def excludeCmd(self,dirname):

            #service on this machine is asked to be excluded for cloud use
            if self.state.cloud_mode:
                if self.state.abort_cloud_mode:
                  self.logger.info('received exclude during cloud mode abort. machine exclude will be resumed..')
                  self.state.abort_cloud_mode=False
                else:
                  self.logger.info('already in cloud mode...')
                  return
            else:
                self.logger.info('machine exclude for cloud initiated. stopping any existing runs...')

            if self.state.cloud_status()>1:
                #execute run cloud stop script in case something is running
                self.state.extinguish_cloud(repeat=True)
                self.logger.error("Unable to switch to cloud mode (external script error).")
                return

            #make sure to not run not acquire resources by inotify while we are here
            with self.resource_lock:
              self.state.cloud_mode=True
              self.state.entering_cloud_mode=True
            #end of locked section

            time.sleep(.1)

            #shut down any quarantined runs
            try:
                for run in self.runList.getQuarantinedRuns():
                    run.Shutdown(True,False)

                requested_stop=False
                listOfActiveRuns = self.runList.getActiveRuns()
                for run in listOfActiveRuns:
                    if not run.pending_shutdown:
                        if len(run.online_resource_list)==0:
                            run.Shutdown(True,False)
                        else:
                            requested_stop=True
                            if dirname.startswith('excludenow'):
                              #let jobs stop without 3 LS drain
                              run.Stop(stop_now=True)
                            else:
                              #regular stop with 3 LS drain
                              run.Stop()

                time.sleep(.1)
                with self.resource_lock:
                    if requested_stop==False:
                        #no runs present, switch to cloud mode immediately
                        self.state.entering_cloud_mode=False
                        self.resInfo.move_resources_to_cloud()
                #end of locked section

                if requested_stop==False:
                    result = self.state.ignite_cloud()
                    cloud_st = self.state.cloud_status()
                    self.logger.info("cloud is on? : "+str(cloud_st == 1) + ' (status code '+str(cloud_st)+')')

            except Exception as ex:
                self.logger.fatal("Unable to clear runs. Will not enter VM mode.")
                self.logger.exception(ex)
                self.state.entering_cloud_mode=False
                self.state.cloud_mode=False


    def includeCmd(self,dirname,fullpath):

            if not self.state.cloud_mode:
                self.logger.warning('received notification to exit from cloud but machine is not in cloud mode!')
                if self.state.cloud_status():
                    self.logger.info('cloud scripts are still running, trying to stop')
                    returnstatus = self.state.extinguish_cloud(repeat=True)
                return

            with self.resource_lock:
                #schedule cloud mode cancel when HLT shutdown is completed
                if self.state.entering_cloud_mode:
                    self.logger.info('include received while entering cloud mode. setting abort flag...')
                    self.state.abort_cloud_mode=True
                    return
                else:
                    #else switch to cloud stopping
                    self.state.exiting_cloud_mode=True
            #end of locked section

            #cloud is being switched off so we don't care if its running status is false
            if not self.state.cloud_status(reportExitCodeError=False):
                self.logger.warning('received command to deactivate cloud, but external script reports that cloud is not running!')

            #stop cloud
            returnstatus = self.state.extinguish_cloud(True)

            retried=False
            attempts=0
            err_attempts=0

            while True:
                last_status = self.state.cloud_status()
                if last_status>=1: #state: running or error
                    self.logger.info('cloud is still active')
                    time.sleep(1)
                    attempts+=1
                    if last_status>1:
                      err_attempts+=1
                      self.logger.warning('external cloud script reports error code' + str(last_status) + '.')
                      if err_attempts>100:
                        #if error is persistent, give up eventually and complain with fatal error 
                        self.state.exiting_cloud_mode=False
                        try:os.remove(fullpath)
                        except:pass
                        time.sleep(1)
                        self.logger.critical('failed to switch off cloud. last status reported: '+str(last_status))
                        return
                    if attempts%60==0 and not retried:
                        self.logger.info('retrying cloud kill after 1 minute')
                        returnstatus = self.state.extinguish_cloud(True)
                        retried=True
                    elif err_attempts and err_attempts%10==0:
                        self.logger.info('retrying cloud kill after 10 status checks returning error')
                        returnstatus = self.state.extinguish_cloud(True)
                        retried=True
                    if attempts>600:
                        self.state.exiting_cloud_mode=False
                        try:os.remove(fullpath)
                        except:pass
                        time.sleep(1)
                        self.logger.critical('failed to switch off cloud after attempting for 10 minutes! last status reports cloud is running...')
                        return
                    continue
                else:
                    self.logger.info('cloud scripts have been deactivated')
                    #switch resources back to normal
                    with self.resource_lock:
                        #self.state.resources_blocked_flag=True
                        self.state.cloud_mode=False
                        self.resInfo.cleanup_resources()
                    break

            self.state.exiting_cloud_mode=False
            try:os.remove(fullpath)
            except:pass
            #sleep some time to let core file notifications to finish
            time.sleep(2)
            self.logger.info('cloud mode in hltd has been switched off')

    def notifyBUSwitch(self,dirname,fullpath):
            #call notify script to move resource file to another NFS path
            #next run should be started from the new NFS path
            pass

    def resourceUpdateCmd(self):

            self.logger.info('resource update event received with '+str(self.state.os_cpuconfig_change))
            #freeze any update during this operation
            self.state.lock.acquire()
            self.resource_lock.acquire()
            l_acquired=True
            try:
                tmp_change = self.state.os_cpuconfig_change
                self.state.os_cpuconfig_change=0
                lastRun = self.runList.getLastOngoingRun()
                #check if this can be done without touching current run
                if tmp_change>0:
                   self.logger.info('adding ' + str(tmp_change))
                   tmp_change = self.resInfo.addResources(tmp_change)
                elif tmp_change<0:
                   self.logger.info('removing ' + str(-tmp_change))
                   tmp_change = self.resInfo.updateIdles(tmp_change,checkLast=False)
                self.logger.info('left ' + str(tmp_change))
                if not tmp_change:pass 
                elif lastRun:
                  #1st case (removed resources): quarantine surplus resources
                  if tmp_change<0:
                    numQuarantine = -tmp_change
                    res_list_join = []
                    for resource in lastRun.online_resource_list:
                      if numQuarantine>0:
                        #if len(resource.cpu)<= numQuarantine:
                        if resource.Stop(delete_resources=True):
                          numQuarantine -= len(resource.cpu)
                          res_list_join.append(resource)
                    self.resource_lock.release()
                    l_acquired=False

                    #join threads with timeout
                    time_left = 120
                    res_list_join_alive=[]
                    for resource in res_list_join:
                      time_start = time.time()
                      try: resource.watchdog.join(time_left) #synchronous stop
                      except: self.logger.info('join failed')
                      self.logger.info('joined resource...')
                      if resource.watchdog.isAlive():
                        res_list_join_alive.append(resource)
                      time_left -= time.time()-time_start
                      if time_left<=0.1:time_left=0.1
                      
                    #invoke terminate if any threads/processes still alive
                    for resource in res_list_join_alive:
                      try:
                        self.logger.info('terminating process ' + str(resource.process.pid))
                        resource.process.terminate()
                      except Exception as ex:
                        self.logger.exception(ex)

                    for resource in res_list_join_alive:
                      try:
                        resource.watchdog.join(30)
                        if resource.watchdog.isAlive():
                          self.logger.info('killing process ' + str(resource.process.pid))
                          resource.process.kill()
                          resource.watchdog.join(10)
                      except:
                        pass

                    res_list_join=[]
                    res_list_join_alive=[]
                    self.resource_lock.acquire()
                    l_acquired=True
                    if numQuarantine<0:
                      #if not a matching number of resources was stopped,add back part of resources later (next run start) 
                      self.state.os_cpuconfig_change=-numQuarantine
                      #let add back resources
                      tmp_change = self.state.os_cpuconfig_change
                  if tmp_change>0:
                    #add more resources
                    left = self.resInfo.addResources(tmp_change)
                    self.state.os_cpuconfig_change=left
                else:
                  #if run is ending (not ongoing, but still keeping resources), update at the next run start
                  self.state.os_cpuconfig_change=tmp_change
            except Exception as ex:
              self.logger.error('failed to process resourceupdate event: ' + str(ex))
              self.logger.exception(ex)
            finally:
              #refresh parameter values
              self.resInfo.calculate_threadnumber()

            if l_acquired:
                self.resource_lock.release()

            self.state.lock.release()

            self.logger.info('end resourceupdate. Left:'+str(self.state.os_cpuconfig_change))
 

    def restartBUCmd(self):

              process = subprocess.Popen(['/opt/hltd/scripts/appliancefus.py'],stdout=subprocess.PIPE)
              raw_str=process.communicate()[0]
              if not isinstance(raw_str,str): raw_str = raw_str.decode("utf-8")
              out_arr = raw_str.split('\n')
              if len(out_arr):
                out = out_arr[0]
                fus=[]
                if process.returncode==0:fus = out.split(',')
                else:
                  dirlist = os.listdir(os.path.join(conf.watch_directory,'appliance','boxes'))
                  for machine in dirlist:
                    if machine == this_machine:continue
                    fus.append(machine)

              def contact_restart(host):
                  host_short = host.split('.')[0]
                  #get hosts from cached ip if possible to avoid hammering DNS
                  try:
                    host = self.rr.boxInfo.FUMap[host_short][0]['ip']
                    self.logger.info(host_short + ' ' + host)
                  except:
                    self.logger.warning(str(host_short) + ' not in FUMap')
                  try:
                    connection = HTTPConnection(host,conf.cgi_port,timeout=20)
                    connection.request("GET",'cgi-bin/restart_cgi.py')
                    time.sleep(.2)
                    response = connection.getresponse()
                    connection.close()
                  except socket.error as ex:
                    self.logger.warning('error contacting '+str(host)+': socket.error: ' + str(ex))
                    #try again in a moment (DNS could be loaded)
                    time.sleep(1)
                    try:
                      connection = HTTPConnection(host,conf.cgi_port,timeout=20)
                      connection.request("GET",'cgi-bin/restart_cgi.py')
                      time.sleep(.2)
                      response = connection.getresponse()
                      connection.close()
                    except socket.error as ex:
                      self.logger.warning('error contacting '+str(host)+': socket.error: ' + str(ex))

                  #catch general exception
                  except Exception as ex:
                    self.logger.warning('problem contacting host' + str(host) + ' ' + str(ex))

              fu_threads = []
              for fu in fus:
                  if not len(fu):continue
                  fu_thread = threading.Thread(target=contact_restart,args=[fu])
                  fu_threads.append(fu_thread)
                  fu_thread.start()
              for fu_thread in fu_threads:
                  fu_thread.join()
 
