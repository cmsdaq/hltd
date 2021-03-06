import os
import time
import subprocess
import threading
import json
import datetime
import logging
import psutil
import struct
import socket

import getnifs
from aUtils import ES_DIR_NAME
from elasticbu import elasticBandBU
from MountManager import MountManagerDummy

MSR_CORE_C1_RES=0x660
MSR_CORE_C3_RESIDENCY=0x3fc
MSR_CORE_C6_RESIDENCY=0x3fd
MSR_CORE_C7_RESIDENCY=0x3fe


class system_monitor(threading.Thread):

    def __init__(self,confClass,stateInfo,resInfo,runList,mountMgr,boxInfo,num_cpus_initial):
        #threading.Thread.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        global conf
        conf = confClass

        self.state = stateInfo
        self.resInfo = resInfo
        self.runList = runList
        self.mm = mountMgr
        self.boxInfo = boxInfo
        self.num_cpus = num_cpus_initial 
        self.num_cpus_real = num_cpus_initial 
 
        try:
          self.hostip = socket.gethostbyname_ex(os.uname()[1])[2][0]
        except Exception as ex:
          #fallback:let BU query DNS
          self.logger.warning('Unable to get IP address from DNS: ' + str(ex))
          self.hostip = os.uname()[1]
        self.hostname = os.uname()[1]

        self.threadEvent = threading.Event()
        self.threadEventStat = threading.Event()
        self.threadEventESBox = threading.Event()
        self.bu_mount_suffix = None
        self.dummyMountMgr = MountManagerDummy()

        self.resetRunningState()

        self.highest_run_number = None #?
        self.cpu_freq_avg_real=0
        self.data_in_MB = 0
        self.mem_frac = 0.

        self.allow_resource_notifications = False
        self.buffered_resource_notification = None
        self.last_good = True
        #cpu timing information
        self.cpu_name,self.cpu_freq,self.cpu_cores,self.cpu_siblings = self.getCPUInfo()
        #start direct injection into central index (fu role)
        self.found_data_interfaces=False
        self.ifs=[]
        self.log_ifconfig=0
        #always start ESBox thread because dynamic core file require it to run
        self.startESBox()

    def resetRunningState(self):

        threading.Thread.__init__(self)
        self.threadEvent.clear()
        self.threadEventStat.clear()
        self.threadEventESBox.clear()
        self.running = True
        self.directory = []
        self.files = []
        self.statThread = None
        self.esBoxThread = None
        self.stale_flag = False
        self.dummyMountMgr.reset()
        self.no_delete_list = []


    def preStart(self):
        if conf.role == 'fu' and not self.mm and not self.bu_mount_suffix: return
        self.rehash()
        if conf.mount_control_path:
            self.startStatNFS()

    #stop current instance, restart on another mount point
    def notifyMaybeChangeBU(self,bu_mount_suffix):
        if not bu_mount_suffix:
          return
        if not self.bu_mount_suffix or self.bu_mount_suffix!=bu_mount_suffix:
          self.logger.info("Changing BU mountpoint, from:"+str(self.bu_mount_suffix)+" to:",bu_mount_suffix)

          #check if this mount point is moving to identical BU from static conf. Then don't delete, just update the file
          #this avoids refusing to join this FU (caused by mechanism to detect FUs which reboot during a run)
          if not self.bu_mount_suffix:
              bu_name_static = self.getBUNameStatic()
              if bu_name_static == bu_mount_suffix:
                  self.no_delete_list = self.files

          #stop, clean up state and restart the monitor
          self.stop()
          self.resetRunningState()
          self.bu_mount_suffix = bu_mount_suffix
          self.startESBox()
          self.preStart()
          self.start()
          self.logger.info("Change BU mountpoint: all handlers restarted")
          #started in new mount point if everything went well
    
    def notifyMaybeRemoveBUMaybe(self,bu_mount_suffix_old):
        if not bu_mount_suffix_old:
          return
        if self.bu_mount_suffix and self.bu_mount_suffix==bu_mount_suffix_old:
              #stop, clean up state and restart the monitor
              self.logger.info("Remove BU mountpoint: " + self.bu_mount_suffix)
              self.stop()
              self.resetRunningState()
              self.bu_mount_suffix = None
 
          
    #called after resource inotify is set up
    def allowResourceNotification(self):
        self.state.lock.acquire()
        self.allow_resource_notifications = True
        if self.buffered_resource_notification:
          with open(self.buffered_resource_notification,'w') as fp:
            pass
        self.state.lock.release()

    def rehash(self):
        if conf.role == 'fu':

            #write only in one location
            if conf.mount_control_path:
                self.logger.info('Updating box info via control interface')
                if self.bu_mount_suffix:
                    self.logger.error("CI-mount/dynamic-mount combination is not supported")
                    self.check_directory = self.check_file = []
                elif self.mm:
                    self.check_directory = [os.path.join(x,'appliance','dn') for x in self.mm.bu_disk_list_ramdisk_instance]
                    self.directory = [os.path.join(self.mm.bu_disk_ramdisk_CI_instance,'appliance','boxes')]
                    self.check_file = [os.path.join(x,self.hostname) for x in self.check_directory]
            else:
                self.logger.info('Updating box info via data interface')
                if self.bu_mount_suffix:
                    self.directory = [os.path.join(conf.bu_base_dir_autofs,self.bu_mount_suffix+'_'+conf.ramdisk_subdirectory,'appliance','boxes')]
                elif self.mm and len(self.mm.bu_disk_list_ramdisk_instance):
                    self.directory = [os.path.join(self.mm.bu_disk_list_ramdisk_instance[0],'appliance','boxes')]


        else:
            self.directory = [os.path.join(conf.watch_directory,'appliance/boxes/')]
            try:
                #if directory does not exist: check if it is renamed to specific name (non-main instance)
                if not os.path.exists(self.directory[0]) and conf.instance=="main":
                    os.makedirs(self.directory[0])
            except OSError:
                pass

            #find boot time so that machine reboot can be detected through the mount point
            try:
                p = subprocess.Popen(["/usr/bin/stat", "-c", "%z", "/proc/"], shell=False, stdout=subprocess.PIPE)
                raw_stdout=p.communicate()[0]
                if not isinstance(raw_stdout,str): raw_stdout = raw_stdout.decode("utf-8")
                self.boot_id=raw_stdout.strip("\n")
                #self.boot_id = p.stdout.read().strip('\n')
            except:
                self.boot_id = "empty"

        self.files = [os.path.join(x,self.hostname) for x in self.directory]

        self.logger.info("rehash found the following BU disk(s):"+str(self.files))
        for disk in self.files:
            self.logger.info(disk)

    def startESBox(self):
        if conf.role == "fu" and not conf.dqm_machine:
            self.esBoxThread = threading.Thread(target=self.runESBox)
            self.esBoxThread.daemon=True #set as daemon thread (not blocking process termination). this should be tested
            self.esBoxThread.start()

    def startStatNFS(self):
        if conf.role == "fu":
            self.statThread = threading.Thread(target=self.runStatNFS)
            self.statThread.start()

    def runStatNFS(self):
        fu_stale_counter=0
        fu_stale_counter2=0
        while self.running:
            if conf.mount_control_path:
                self.threadEventStat.wait(2)
            time_start = time.time()
            err_detected = False
            try:
                #check for NFS stale file handle
                if self.bu_mount_suffix:
                        pass
                        #TODO: implement check of the active submount
                elif self.mm:
                  for disk in  self.mm.bu_disk_list_ramdisk:
                    mpstat = os.stat(disk)
                  for disk in  self.mm.bu_disk_list_output:
                    mpstat = os.stat(disk)
                  if self.mm.bu_disk_ramdisk_CI:
                    disk = self.mm.bu_disk_ramdisk_CI
                    mpstat = os.stat(disk)
                #no issue if we reached this point
                fu_stale_counter = 0
            except (IOError,OSError) as ex:
                err_detected=True
                if ex.errno == 116:
                    if fu_stale_counter==0 or fu_stale_counter%500==0:
                        self.logger.fatal('detected stale file handle: '+str(disk))
                        #if BU boot id not same, trigger local suspend (suspend) mechanism which will perform remount
                        if not self.buBootIdCheck():
                            with open(os.path.join(conf.watch_directory,'suspend'),'w'):pass
                else:
                    self.logger.warning('stat mountpoint ' + str(disk) + ' caught Error: '+str(ex))
                fu_stale_counter+=1
                err_detected=True
            except Exception as ex:
                err_detected=True
                self.logger.warning('stat mountpoint ' + str(disk) + ' caught exception: '+str(ex))

            #if stale handle checks passed, check if write access and timing are normal
            #for all data network ramdisk mountpoints
            if conf.mount_control_path and not err_detected:
                try:
                    for mfile in self.check_file:
                        with open(mfile,'w') as fp:
                            fp.write('{}')
                        fu_stale_counter2 = 0
                        #os.stat(mfile)
                except IOError as ex:
                    err_detected = True
                    fu_stale_counter2+=1
                    if ex.errno==2:
                        #still an error if htld on BU did not create 'appliance/dn' dir
                        if fu_stale_counter2==0 or fu_stale_counter2%20==0:
                            self.logger.warning('unable to update '+mfile+ ' : '+str(ex))
                    else:
                        self.logger.error('update file ' + mfile + ' caught Error:'+str(ex))
                except Exception as ex:
                    err_detected = True
                    self.logger.error('update file ' + mfile + ' caught exception:'+str(ex))

            #measure time needed to do these actions. stale flag is set if it takes more than 10 seconds
            stat_time_delta = time.time()-time_start
            if stat_time_delta>5:
                if conf.mount_control_path:
                    self.logger.warning("unusually long time ("+str(stat_time_delta)+"s) was needed to perform file handle and boxinfo stat check")
                else:
                    self.logger.warning("unusually long time ("+str(stat_time_delta)+"s) was needed to perform stale file handle check")
            if stat_time_delta>5 or err_detected:
                self.stale_flag=True
            else:
                #clear stale flag if successful
                self.stale_flag=False

            #no loop if called inside main loop
            if not conf.mount_control_path:
                return

    def buBootIdCheck(self):
       def checkStale(mm):
         if mm is None or not mm: return True
         #skip duplicate check
         if mm.stale_handle_remount_required or self.state.suspended: return False
         #not using default static boot config, store boot ID in this class
         if conf.role=='fu' and len(self.directory):
           if mm.buBootId is None:
               mm.buBootId = self.buBootIdFetch(self.directory[0])
           elif mm.buBootId is not None:
               id_check =  self.buBootIdFetch(self.directory[0])
               if id_check != mm.buBootId: #check if there is new boot timestamp
                   self.logger.warning('new BU boot id detected. old:' + str(mm.buBootId) + ' new:' + str(id_check))
                   mm.stale_handle_remount_required = True
                   return False
         return True

       #check on either dynamic or non-dynamic
       if self.bu_mount_suffix:
         return checkStale(self.dummyMountMgr)
       else:
         return checkStale(self.mm)
       

    def buBootIdFetch(self,buboxdir):
        try:
          listed = os.listdir(buboxdir)
          for bf in listed:
            if bf.startswith('bu-') or bf.startswith('dvbu-')  or bf.startswith('d3vrubu-') or (self.hostname.startswith('dvfu-') and bf.startswith('dvrubu-')):
              with open(os.path.join(buboxdir,bf),'r') as fp:
                return json.load(fp)['boot_id']
          #make this work for test host which doesn't begin with *bu- name
          for bf in listed:
            bf_short = bf.split('.')[0]
            if self.bu_mount_suffix and bf_short == self.bu_mount_suffix:
              with open(os.path.join(buboxdir,bf),'r') as fp:
                return json.load(fp)['boot_id']

        except Exception as ex:
          self.logger.warning('unable to read BU boot_id: '+str(ex))
        return None

    def run(self):
        try:
            self.logger.debug('entered system monitor thread ')
            res_path_temp = os.path.join(conf.watch_directory,'appliance','resource_summary_temp')
            res_path = os.path.join(conf.watch_directory,'appliance','resource_summary')
            selfhost = os.uname()[1]
            boxinfo_update_attempts=0
            counter=0
            fu_watchdir_is_mountpoint = os.path.ismount(conf.watch_directory)

            if conf.mon_bu_cpus:
                vtmp_old = self.getIntelCPUPerfVec()
                ts_old_percpu = time.time()
            if conf.role == 'fu' and not self.mm and not self.bu_mount_suffix:
                return

            while self.running:
                self.threadEvent.wait(5 if counter>0 else 1) #TODO:interrupt this event in case new file has to be written to the new BU
                counter+=1
                counter=counter%5
                if self.state.suspended: continue
                tstring = datetime.datetime.utcfromtimestamp(time.time()).isoformat()

                #update BU boot id if not set
                if conf.role=='fu' and self.mm and not self.mm.buBootId and len(self.directory): self.mm.buBootId = self.buBootIdFetch(self.directory[0])

                ramdisk = None
                if conf.role == 'bu':
                    ramdisk = os.statvfs(conf.watch_directory)
                    ramdisk_occ=1
                    try:
                      ramdisk_occ_num = float((ramdisk.f_blocks - ramdisk.f_bavail)*ramdisk.f_bsize - self.mm.ramdisk_submount_size)
                      ramdisk_occ_den = float(ramdisk.f_blocks*ramdisk.f_bsize - self.mm.ramdisk_submount_size)
                      ramdisk_occ = ramdisk_occ_num/ramdisk_occ_den
                    except:pass
                    if ramdisk_occ<0:
                        ramdisk_occ=0
                        self.logger.info('incorrect ramdisk occupancy:' + str(ramdisk_occ))
                    if ramdisk_occ>1:
                        ramdisk_occ=1
                        self.logger.info('incorrect ramdisk occupancy:' + str(ramdisk_occ))

                    #init
                    resource_count_idle = 0
                    resource_count_used = 0
                    resource_count_broken = 0
                    resource_count_quarantined = 0
                    resource_count_stale = 0
                    resource_count_pending = 0
                    resource_count_activeRun = 0
                    cloud_count = 0
                    lastFURuns = []
                    lastFUrun=-1
                    activeRunQueuedLumisNum = -1
                    activeRunCMSSWMaxLumi = -1
                    activeRunLSWithOutput = -1
                    output_bw_mb = 0
                    active_run_output_bw_mb = 0
                    active_run_lumi_bw_mb = 0
                    active_res = 0

                    fu_data_alarm=False

                    current_time = time.time()
                    stale_machines = []
                    cpufrac_vector = []
                    cpufreq_vector = []
                    fu_data_net_in = 0
                    fu_data_net_in_vector = []

                    #counters used to calculate if all FUs are in cloud (or switching to cloud)
                    #stale FUs are not used in calculation
                    reporting_fus = 0
                    reporting_fus_rescount = 0
                    reporting_fus_cloud = 0
                    num_hlt_errors = {}
                    num_hlt_errors_lastrun = 0.
                    fu_cpu_name="N/A"
                    fu_phys_cores=0
                    fu_ht_cores=0
                    mem_frac_avg=0.
                    mem_frac_norm=0

                    try:
                        current_runnumber = self.runList.getLastRun().runnumber
                    except:
                        current_runnumber=0
                    fumapKeys = list(self.boxInfo.FUMap.keys())[:]
                    fumapKeys.sort()
                    for key in fumapKeys:
                        if key==selfhost:continue
                        try:
                            edata,etime,lastStatus = self.boxInfo.FUMap[key]
                        except:continue #deleted?
                        if current_time - etime > 10 or edata is None: continue
                        try:
                            try:
                                if edata['version']!=self.boxInfo.boxdoc_version:
                                    self.logger.warning('box file version mismatch from '+str(key)+' got:'+str(edata['version'])+' required:'+str(self.boxInfo.boxdoc_version))
                                    continue
                            except:
                                self.logger.warning('box file version for '+str(key)+' not found')
                                continue

                            #find FU CPU name
                            try:
                              if fu_cpu_name=="N/A":
                                fu_cpu_name = edata['cpuName']
                              elif fu_cpu_name != edata['cpuName']:
                                fu_cpu_name = "Unknown"
                            except:
                              #ignore if not found in fu box document
                              pass

                            #pick value from FU which is max. behind (and initialized)
                            maxlsout = edata['activeRunMaxLSOut']
                            if maxlsout!=-1:
                              if activeRunLSWithOutput == -1:
                                activeRunLSWithOutput=maxlsout
                              else:
                                activeRunLSWithOutput=min(activeRunLSWithOutput,maxlsout)

                            #sum bandwidth over FUs (last 10 sec). This is approximate because measured intervals are different.
                            #it should give good approximation at high output rate when FU output traffic is continuous rather than bursty
                            output_bw_mb+=edata['outputBandwidthMB']
                            active_run_output_bw_mb+=edata['activeRunOutputMB']
                            active_run_lumi_bw_mb+=edata['activeRunLSBWMB']

                            r_idle=edata['idles']
                            r_used=edata['used']
                            r_quar=edata['quarantined']
                            r_broken=edata['broken']
                            r_cloud=edata['cloud']

                            if edata['detectedStaleHandle']:
                                stale_machines.append(str(key))
                                resource_count_stale+=r_idle+r_used+r_broken
                            else:
                                if current_runnumber in  edata['activeRuns']:
                                    resource_count_activeRun += edata['used_activeRun']+edata['broken_activeRun']
                                active_addition =0

                                if edata['cloudState'] == "resourcesReleased":
                                    resource_count_pending += edata['idles']
                                else:
                                    resource_count_idle+=r_idle
                                    active_addition+=r_idle

                                active_addition+=r_used
                                active_addition+=r_broken
                                resource_count_used+=r_used
                                resource_count_broken+=r_broken
                                resource_count_quarantined+=r_quar

                                reporting_fus+=1
                                reporting_fus_rescount+=r_idle+r_used+r_broken+r_quar+r_cloud
                                #active resources reported to BU if cloud state is off
                                if edata['cloudState'] == "off":
                                    active_res+=active_addition
                                    cpufrac_vector.append(edata['sysCPUFrac'])
                                    cpufreq_vector.append(edata['cpu_MHz_avg_real'])
                                    fu_data_net_in+=edata['dataNetIn']
                                    fu_data_net_in_vector.append(edata['dataNetIn'])
                                    try:
                                      fu_phys_cores+=edata["cpu_phys_cores"]
                                      fu_ht_cores+=edata["cpu_hyperthreads"]
                                    except:pass
                                    #new:
                                    try:
                                      mem_frac_avg+=edata["mem_frac"]
                                      mem_frac_norm+=1
                                    except:pass
                                else:
                                    reporting_fus_cloud+=1

                            cloud_count+=r_cloud

                            fu_data_alarm = edata['fuDataAlarm'] or fu_data_alarm
                        except Exception as ex:
                            self.logger.warning('problem updating boxinfo summary: '+str(ex))
                        try:
                            last_run = edata['activeRuns'][-1]
                            lastFURuns.append(last_run)
                            for rs in edata['activeRunStats']:
                                entry_run=rs['run']
                                try:
                                    num_hlt_errors[entry_run]+=rs['errorsRes']
                                except:
                                    num_hlt_errors[entry_run]=rs['errorsRes']
                        except:pass
                    res_per_fu=0 if not reporting_fus else reporting_fus_rescount//reporting_fus
                    if len(stale_machines) and counter==1:
                        self.logger.warning("detected stale box resources: "+str(stale_machines))
                    fuRuns = sorted(list(set(lastFURuns)))
                    if len(fuRuns)>0:
                        lastFUrun = fuRuns[-1]
                        if lastFUrun>0:
                          try:
                            #divide with max number of times each process can be (re)started: 1 + restart limit
                            num_hlt_errors_lastrun = num_hlt_errors[lastFUrun]/(1.+conf.process_restart_limit)
                          except:
                            num_hlt_errors_lastrun = 0.
                        #second pass
                        for key in self.boxInfo.FUMap: #no need to sort
                            if key==selfhost:continue
                            try:
                                edata,etime,lastStatus = self.boxInfo.FUMap[key]
                            except:continue #deleted?
                            if current_time - etime > 10 or edata is None: continue
                            try:
                                try:
                                    if edata['version']!=self.boxInfo.boxdoc_version: continue
                                except: continue
                                lastrun = edata['activeRuns'][-1]
                                if lastrun==lastFUrun:
                                    qlumis = int(edata['activeRunNumQueuedLS'])
                                    if qlumis>activeRunQueuedLumisNum:activeRunQueuedLumisNum=qlumis
                                    maxcmsswls = int(edata['activeRunCMSSWMaxLS'])
                                    if maxcmsswls>activeRunCMSSWMaxLumi:activeRunCMSSWMaxLumi=maxcmsswls
                            except:pass
                    if mem_frac_norm:
                        mem_frac_avg=mem_frac_avg/mem_frac_norm
                    #signal BU to stop requesting if all FUs switch to cloud. This will coincide with active_resources being reported as 0
                    #flag is disabled if there are no non-stale FUs
                    bu_stop_requests_flag=True if reporting_fus>0 and reporting_fus_cloud==reporting_fus else False
                    res_doc = {
                                "active_resources":active_res,
                                "active_resources_activeRun":resource_count_activeRun,
                                "active_resources_oldRuns":active_res - resource_count_activeRun-resource_count_idle,
                                #"active_resources":resource_count_activeRun,
                                "idle":resource_count_idle,
                                "used":resource_count_used,
                                "broken":resource_count_broken,
                                "quarantined":resource_count_quarantined,
                                "stale_resources":resource_count_stale,
                                "cloud":cloud_count,
                                "pending_resources":resource_count_pending,
                                "activeFURun":lastFUrun,
                                "activeRunNumQueuedLS":activeRunQueuedLumisNum,
                                "activeRunCMSSWMaxLS":activeRunCMSSWMaxLumi,
                                "activeRunLSWithOutput":activeRunLSWithOutput,
                                "outputBandwidthMB":output_bw_mb,
                                "activeRunOutputMB":active_run_output_bw_mb,
                                "activeRunLSBWMB":active_run_lumi_bw_mb,
                                "activeRunHLTErr":num_hlt_errors_lastrun,
                                "ramdisk_occupancy":ramdisk_occ,
                                "fuDiskspaceAlarm":fu_data_alarm,
                                "bu_stop_requests_flag":bu_stop_requests_flag,
                                "fuSysCPUFrac":cpufrac_vector,
                                "fuSysCPUMHz":cpufreq_vector,
                                "fuDataNetIn":fu_data_net_in,
                                "resPerFU":int(round(res_per_fu)),
                                "fuCPUName":fu_cpu_name,
                                "buCPUName":self.cpu_name,
                                "activePhysCores":fu_phys_cores,
                                "activeHTCores":fu_ht_cores,
                                "fuMemFrac":mem_frac_avg,
                                "isGlobalRun":self.state.isGlobalRun,
                                "daqSystem":self.state.daqSystem,
                                "daqInstance":self.state.daqInstance,
                                "fuGroup":self.state.fuGroup
                              }
                    #BU CPU montoring of C-states and frequency
                    if conf.mon_bu_cpus:
                        res_doc["fuDataNetIn_perfu"]=fu_data_net_in_vector #per Fu bandwidth (sorted)
                        try:
                            vtmp_new = self.getIntelCPUPerfVec()
                            ts_new_percpu = time.time()
                            d_ts = ts_new_percpu - ts_old_percpu
                            ts_old_percpu = ts_new_percpu

                            mhz_vec = []
                            c1_vec = []
                            c3_vec = []
                            c6_vec = []
                            c7_vec = []
                            s0_vec = []
                            s1_vec = []
                            s2_vec = []
                            s3_vec = []
                            load_factor = 0.
                            load_factor_0 = 0.
                            load_factor_1 = 0.
                            cpucount = len(vtmp_new)
                            for i,x in enumerate(vtmp_new):
                                d_tsc = vtmp_new[i][0]-vtmp_old[i][0]
                                d_mperf = vtmp_new[i][1]-vtmp_old[i][1]
                                d_aperf = vtmp_new[i][2]-vtmp_old[i][2]
                                mhz = (d_tsc * d_aperf) / (1000000. * d_mperf * d_ts)
                                mhz_vec.append(int(mhz))
                                tsc_MHz = d_tsc / (1000000. * d_ts)
                                load_factor+=mhz/(tsc_MHz * cpucount)
                                if i<cpucount//2:
                                  load_factor_0+=mhz/(tsc_MHz * cpucount*0.5)
                                else:
                                  load_factor_1+=mhz/(tsc_MHz * cpucount*0.5)
                                d_c3 = vtmp_new[i][4]-vtmp_old[i][4]
                                d_c6 = vtmp_new[i][5]-vtmp_old[i][5]
                                d_c7 = vtmp_new[i][6]-vtmp_old[i][6]
                                c3_vec.append((d_c3*1.)/d_tsc)
                                c6_vec.append((d_c6*1.)/d_tsc)
                                c7_vec.append((d_c7*1.)/d_tsc)
                                #c1 formula
                                c1 = d_tsc - d_mperf -d_c3 -d_c6 -d_c7
                                if c1<0: c1=0
                                c1_vec.append(c1/(1.*d_tsc))
                                
                                s_tot = (vtmp_new[i][7] + vtmp_new[i][8] + vtmp_new[i][9] + vtmp_new[i][10] - vtmp_old[i][7]-vtmp_old[i][8]-vtmp_old[i][9]-vtmp_old[i][10])*1.
                                if s_tot!=0.:
                                  s0_vec.append((vtmp_new[i][7]-vtmp_old[i][7])/s_tot)
                                  s1_vec.append((vtmp_new[i][8]-vtmp_old[i][8])/s_tot)
                                  s2_vec.append((vtmp_new[i][9]-vtmp_old[i][9])/s_tot)
                                  s3_vec.append((vtmp_new[i][10]-vtmp_old[i][10])/s_tot)

                                else:
                                  s0_vec.append(0.)
                                  s1_vec.append(0.)
                                  s2_vec.append(0.)
                                  s3_vec.append(0.)


                            #store next
                            vtmp_old = vtmp_new

                            res_doc["bu_percpu_MHz_real"] = mhz_vec
                            res_doc["bu_cpu_loadfactor"] = [load_factor,load_factor_0,load_factor_1]
                            res_doc["bu_percpu_c1_frac"] = c1_vec
                            res_doc["bu_percpu_c3_frac"] = c3_vec
                            res_doc["bu_percpu_c6_frac"] = c6_vec
                            res_doc["bu_percpu_c7_frac"] = c7_vec
                            res_doc["bu_percpu_s0_poll"] = s0_vec
                            res_doc["bu_percpu_s1_c1"] = s1_vec
                            res_doc["bu_percpu_s2_c1e"] = s2_vec
                            res_doc["bu_percpu_s3_c6"] = s3_vec
                        except Exception as ex:
                            self.logger.exception(ex)

                    try:
                        with open(res_path_temp,'w') as fp:
                            json.dump(res_doc,fp,indent=True)
                        os.rename(res_path_temp,res_path)
                    except Exception as ex:
                        self.logger.exception(ex)
                    res_doc['fm_date']=tstring
                    try:self.boxInfo.updater.ec.injectSummaryJson(res_doc)
                    except:pass
                    try:
                        if lastFUrun>0:
                            if not self.highest_run_number or self.highest_run_number<lastFUrun:
                                self.highest_run_number=lastFUrun

                    except:pass

                for mfile in self.files:
                    if conf.role == 'fu':

                            #check if stale file handle (or slow access)
                        if not conf.mount_control_path:
                            self.runStatNFS()

                        if fu_watchdir_is_mountpoint:
                            dirstat = os.statvfs(conf.watch_directory)
                            d_used = ((dirstat.f_blocks - dirstat.f_bavail)*dirstat.f_bsize)>>20
                            d_total =  (dirstat.f_blocks*dirstat.f_bsize)>>20
                        else:
                            p = subprocess.Popen("du -s --exclude " + ES_DIR_NAME + " --exclude mon --exclude open " + str(conf.watch_directory), shell=True, stdout=subprocess.PIPE)
                            
                            raw_stdout=p.communicate()[0]
                            if not isinstance(raw_stdout,str): raw_stdout = raw_stdout.decode("utf-8")
                            try:
                              out = raw_stdout.split('\t')[0]
                              d_used = int(out)>>10
                            except:
                              d_used=0
                            d_total = conf.max_local_disk_usage

                        lastrun = self.runList.getLastRun()
                        n_used_activeRun=0
                        n_broken_activeRun=0

                        try:
                            #if cloud_mode==True and entering_cloud_mode==True:
                            #  n_idles = 0
                            #  n_used = 0
                            #  n_broken = 0
                            #  n_cloud = len(os.listdir(cloud))+len(os.listdir(idles))+len(os.listdir(used))+len(os.listdir(broken))
                            #else:
                            active_runs = self.runList.getActiveRunNumbers()
                            usedlist = os.listdir(self.resInfo.used)
                            brokenlist = os.listdir(self.resInfo.broken)
                            if lastrun:
                                try:
                                    n_used_activeRun = lastrun.countOwnedResourcesFrom(usedlist)
                                    n_broken_activeRun = lastrun.countOwnedResourcesFrom(brokenlist)
                                except:pass
                            n_idles = len(os.listdir(self.resInfo.idles))
                            n_used = len(usedlist)
                            n_broken = len(brokenlist)
                            n_cloud = len(os.listdir(self.resInfo.cloud))
                            n_quarantined = len(os.listdir(self.resInfo.quarantined))-self.resInfo.num_excluded
                            if n_quarantined<0: n_quarantined=0
                            numQueuedLumis,maxCMSSWLumi,maxLSWithOutput,outBW,lumiBW=self.getLumiQueueStat()
                            #reset per-run BW values if no active run
                            if len(active_runs)==0:lumiBW=outBWrun=0.
                            outBWrun=outBW
                            outBW+=self.getQueueStatusPreviousRunsBW()

                            cloud_state = self.getCloudState()

                            boxdoc = {
                                'fm_date':tstring,
                                'idles' : n_idles,
                                'used' : n_used, # #TODO:minus used processes on previous run prior to switch tu a current BU (calculate inside process, keep track of BUs used per run)
                                'broken' : n_broken,
                                'used_activeRun' : n_used_activeRun,
                                'broken_activeRun' : n_broken_activeRun,
                                'cloud' : n_cloud,
                                'quarantined' : n_quarantined,
                                'usedDataDir' : d_used,
                                'totalDataDir' : d_total,
                                'fuDataAlarm' : d_used > 0.9*d_total,
                                'activeRuns' :   active_runs,
                                'activeRunNumQueuedLS':numQueuedLumis,
                                'activeRunCMSSWMaxLS':maxCMSSWLumi,
                                'activeRunStats':self.runList.getStateDoc(),
                                'cloudState':cloud_state,
                                'detectedStaleHandle':self.stale_flag,
                                'version':self.boxInfo.boxdoc_version,
                                'ip':self.hostip,
                                'activeRunMaxLSOut':maxLSWithOutput,
                                'outputBandwidthMB':outBW*0.000001,
                                'activeRunOutputMB':outBWrun*0.000001,
                                'activeRunLSBWMB':lumiBW*0.000001,
                                "sysCPUFrac":psutil.cpu_percent()*0.01,
                                "cpu_MHz_avg_real":self.cpu_freq_avg_real,
                                "dataNetIn":self.data_in_MB,
                                "cpuName":self.cpu_name,
                                "cpu_phys_cores":self.cpu_cores,
                                "cpu_hyperthreads":self.cpu_siblings,
                                "mem_frac":self.mem_frac,
                                "isGlobalRun":self.state.isGlobalRun,
                                "daqSystem":self.state.daqSystem,
                                "daqInstance":self.state.daqInstance,
                                "fuGroup":self.state.fuGroup
                            }
                            with open(mfile,'w') as fp: #recalculate path according to new BU switched. Delete file from the old BU if moving BU
                                json.dump(boxdoc,fp,indent=True)
                            boxinfo_update_attempts=0

                        except (IOError,OSError) as ex:
                            self.logger.warning('boxinfo file write failed :'+str(ex))
                            #detecting stale file handle on recreated loop fs and remount
                            if conf.instance!='main' and (ex.errno==116 or ex.errno==2) and boxinfo_update_attempts>=5:
                                boxinfo_update_attempts=0
                                try:os.unlink(os.path.join(conf.watch_directory,'suspend'))
                                except:pass
                                with open(os.path.join(conf.watch_directory,'suspend'),'w'):
                                    pass
                                time.sleep(1)
                            boxinfo_update_attempts+=1
                        except Exception as ex:
                            self.logger.warning('exception on boxinfo file write failed : +'+str(ex))

                    if conf.role == 'bu':
                        outdir = os.statvfs('/fff/output')
                        boxdoc = {
                            'fm_date':tstring,
                            'usedRamdisk':((ramdisk.f_blocks - ramdisk.f_bavail)*ramdisk.f_bsize - self.mm.ramdisk_submount_size)>>20,
                            'totalRamdisk':(ramdisk.f_blocks*ramdisk.f_bsize - self.mm.ramdisk_submount_size)>>20,
                            'usedOutput':((outdir.f_blocks - outdir.f_bavail)*outdir.f_bsize)>>20,
                            'totalOutput':(outdir.f_blocks*outdir.f_bsize)>>20,
                            'activeRuns':self.runList.getActiveRunNumbers(),
                            "version":self.boxInfo.boxdoc_version,
                            "boot_id":self.boot_id,
                            "cpuName":self.cpu_name,
                            "isGlobalRun":self.state.isGlobalRun,
                            "daqSystem":self.state.daqSystem,
                            "daqInstance":self.state.daqInstance,
                            "fuGroup":self.state.fuGroup
                        }
                        try:
                            with open(mfile,'w') as fp: #TODO:
                                json.dump(boxdoc,fp,indent=True)
                            boxinfo_update_attempts=0
                        except IOError as ex:
                            if ex.errno==11 and boxinfo_update_attempts<5: #Resource temporarily unavailable
                                self.logger.warning("Resource temporarily unavailable on attempting to write: "+ mfile)
                                boxinfo_update_attempts+=1
                            else:
                                self.logger.exception(ex)
                                boxinfo_update_attempts=0
                        except Exception as ex:
                            self.logger.exception(ex)

        except Exception as ex:
            self.logger.exception(ex)

        for mfile in self.files:
            if mfile in self.no_delete_list:continue
            try:
                os.remove(mfile)
            except OSError:
                pass

        self.logger.debug('exiting system monitor thread ')

    def getLumiQueueStat(self):
        try:
            with open(os.path.join(conf.watch_directory,
                                   'run'+str(self.runList.getLastRun().runnumber).zfill(conf.run_number_padding),
                                   'open','queue_status.jsn'),'r') as fp:

                #fcntl.flock(fp, fcntl.LOCK_EX)
                statusDoc = json.load(fp)
                return statusDoc["numQueuedLS"],statusDoc["CMSSWMaxLS"],statusDoc["maxLSWithOutput"],statusDoc["outputBW"],statusDoc["lumiBW"]
        except:
            return -1,-1,-1,0,0

    def getQueueStatusPreviousRunsBW(self):
        #get output from all previous active runs, in case there are any
        outBW=0
        lastRun = self.runList.getLastRun()
        for runObj in self.runList.getActiveRuns():
            if runObj!=lastRun:
                try:
                    with open(os.path.join(conf.watch_directory,
                              'run'+str(runObj.getLastRun().runnumber).zfill(conf.run_number_padding),
                              'open','queue_status.jsn'),'r') as fp:
                        outBW += int(json.load(fp)["outputBW"])
                except:
                    continue
        if outBW!=0: self.logger.info('detected output badwidth from previous runs: '+str(outBW*0.000001)+ ' MB/s')
        return outBW


    def getCPUInfo(self):
        try:
            cpu_name = ""
            cpu_freq = 0.
            cpu_cores = 0
            cpu_siblings = 0
            num_cpu = 1
            with open('/proc/cpuinfo','r') as fi:
              for line in fi.readlines():
                if line.startswith("model name") and not cpu_name:
                    for word in line[line.find(':')+1:].split():
                      if word=='' or '(R)' in word  or '(TM)' in word or 'CPU' in word or '@' in word :continue
                      if 'GHz' in word: cpu_freq = float(word[:word.find('GHz')])
                      else:
                        if cpu_name: cpu_name = cpu_name+" "+word
                        else: cpu_name=word

                if line.startswith("siblings") and not cpu_siblings:
                    cpu_siblings = int(line.split()[-1])
                if line.startswith("cpu cores") and not cpu_cores:
                    cpu_cores = int(line.split()[-1])
                if line.startswith("physical id"):
                    phys_id = int(line.split()[-1])
                    if phys_id+1>num_cpu: num_cpu=phys_id+1
            return cpu_name,cpu_freq,num_cpu*cpu_cores,num_cpu*cpu_siblings
        except:
            return "",0.,0,0

    def getCPUFreqInfo(self):
      avg=0.
      avg_c = 0
      try:
        #obtain cpu frequencies and get avg (in GHz)
        #TODO:replace shell script call with info from Intel MSR
        #p = subprocess.Popen('/usr/bin/cpupower frequency-info | grep "current CPU"', shell=True, stdout=subprocess.PIPE)
        p = subprocess.Popen(['/usr/bin/cpupower', 'frequency-info'], shell=False, stdout=subprocess.PIPE)
        raw_stdout=p.communicate()[0]
        if not isinstance(raw_stdout,str): raw_stdout = raw_stdout.decode("utf-8")
        std_out=[ x for x in raw_stdout.split("\n") if x.startswith("current CPU") ]
        for stdl in std_out:
          avg+=float(stdl.strip().split()[4])*1000
          avg_c+=1
      except:pass
      if avg_c == 0:return 0
      else: return int(avg/avg_c)


    def testCPURange(self):
      cnt=0
      while True:
        try: 
          fd = os.open("/dev/cpu/"+str(cnt)+"/msr",os.O_RDONLY)
          os.close(fd)
        except:
          return cnt
        cnt+=1

    def getIntelCPUPerfAvgs(self):
      tsc=0
      aperf=0
      mperf=0
      cnt=0
      while cnt<self.num_cpus_real:
        try:
          fd = None
          fd = os.open("/dev/cpu/"+str(cnt)+"/msr",os.O_RDONLY)
          os.lseek(fd,0x10,os.SEEK_SET)
          tsc += struct.unpack("Q",os.read(fd,8))[0]
          os.lseek(fd,0xe7,os.SEEK_SET)
          mperf += struct.unpack("Q",os.read(fd,8))[0]
          os.lseek(fd,0xe8,os.SEEK_SET)
          aperf += struct.unpack("Q",os.read(fd,8))[0]
          cnt+=1
          os.close(fd)
          self.last_good=True
        except OSError as ex:
          if ex.errno==5:
            if self.last_good:
              self.logger.warning(str(ex))
            self.last_good=False
            try:os.close(fd)
            except:pass
            return 0,0,0
 
        except IOError as ex:
          self.logger.warning(str(ex))
          try:os.close(fd)
          except:pass
          return 0,0,0
      return tsc,mperf,aperf

    def getIntelCPUPerfVec(self):
      ret=[]
      cnt=0
      #while cnt<self.cpu_siblings:
      while cnt<self.cpu_cores:
        try:
          fd = None
          fd = os.open("/dev/cpu/"+str(cnt)+"/msr",os.O_RDONLY)
          os.lseek(fd,0x10,os.SEEK_SET)
          tsc = struct.unpack("Q",os.read(fd,8))[0]
          os.lseek(fd,0xe7,os.SEEK_SET)
          mperf = struct.unpack("Q",os.read(fd,8))[0]
          os.lseek(fd,0xe8,os.SEEK_SET)
          aperf = struct.unpack("Q",os.read(fd,8))[0]

          c3 = c6 = c7 = s0 = s1 = s2 = s3 = 0

          #following will work only on Intel devices:
          try:
            os.lseek(fd,MSR_CORE_C3_RESIDENCY,os.SEEK_SET)
            c3 = struct.unpack("Q",os.read(fd,8))[0]

            os.lseek(fd,MSR_CORE_C6_RESIDENCY,os.SEEK_SET)
            c6 = struct.unpack("Q",os.read(fd,8))[0]

            os.lseek(fd,MSR_CORE_C7_RESIDENCY,os.SEEK_SET)
            c7 = struct.unpack("Q",os.read(fd,8))[0]

            with open("/sys/devices/system/cpu/cpu"+str(cnt)+"/cpuidle/state0/usage",'r') as fr:
              val = fr.read()
              s0 = int(val)

            with open("/sys/devices/system/cpu/cpu"+str(cnt)+"/cpuidle/state1/usage",'r') as fr:
              val = fr.read()
              s1 = int(val)


            with open("/sys/devices/system/cpu/cpu"+str(cnt)+"/cpuidle/state2/usage",'r') as fr:
              val = fr.read()
              s2 = int(val)


            with open("/sys/devices/system/cpu/cpu"+str(cnt)+"/cpuidle/state3/usage",'r') as fr:
              val = fr.read()
              s3 = int(val)

          except:
            pass

          ret.append([tsc,mperf,aperf,0,c3,c6,c7,s0,s1,s2,s3])
            
          cnt+=1
          os.close(fd)
        except (IOError,OSError) as ex:
          self.logger.warning(str(ex))
          try:os.close(fd)
          except:pass
          return []
      return ret


    def getMEMInfo(self):
        return dict((i.split()[0].rstrip(':'),int(i.split()[1])) for i in open('/proc/meminfo').readlines())

    def findMountInterfaces(self): #TODO: find only last interface switched to. Also file_broker address needs to be adjusted. How to discover it? automounter interfaces?
        #also file broker stuff should be passed by the script, not read from current config
        ipaddrs = []
        for line in open('/proc/mounts').readlines():
          mountpoint = line.split()[1]
          if mountpoint.startswith('/fff/'):
            opts = line.split()[3].split(',')
            for opt in opts:
              if opt.startswith('clientaddr='):
                ipaddrs.append(opt.split('=')[1])
        ipaddrs = list(set(ipaddrs))
        ifs = []
        #update list and reset counters only if interface is missing from the previous list 
        if len(ipaddrs)>len(self.ifs):
          self.found_data_interfaces=True
          ifcdict = getnifs.get_network_interfaces()
          for ifc in ifcdict:
            name = ifc.name
            addresses = ifc.addresses
            if 2 in addresses and len(addresses[2]):
              if addresses[2][0] in ipaddrs:
                ifs.append(name)
                if self.log_ifconfig<2:
                  self.logger.info('monitoring '+name)
          ifs = list(set(ifs))
          self.ifs = ifs
          self.ifs_in=0
          self.ifs_out=0
          self.ifs_last = 0
          self.getRatesMBs(silent=self.log_ifconfig<2) #initialize
          self.threadEventESBox.wait(0.1)
        self.log_ifconfig+=1

    def getRatesMBs(self,silent=True):
        try:
          sum_in=0
          sum_out=0
          for ifc in self.ifs:
            sum_in+=int(open('/sys/class/net/'+ifc+'/statistics/rx_bytes').read())
            sum_out+=int(open('/sys/class/net/'+ifc+'/statistics/tx_bytes').read())
          new_time = time.time()
          old_time = self.ifs_last
          delta_t = new_time-self.ifs_last
          self.ifs_last = new_time
          #return 0 if this is first read (last counters=0)
          if self.ifs_in==0 or self.ifs_out==0:
            self.ifs_in = sum_in
            self.ifs_out = sum_out
            return [0,0,new_time-old_time]
          else: 
            divisor = 1. / (delta_t*1024*1024.)
            delta_in = (sum_in - self.ifs_in) * divisor # Bytes/ms >> 10 == MB/s
            delta_out = (sum_out - self.ifs_out) * divisor
            self.ifs_in = sum_in
            self.ifs_out = sum_out
            return [delta_in,delta_out,new_time-old_time]
        except Exception as ex:
          if not silent:
            self.logger.exception(ex)
          return [0,0,0]


    def getBUNameStatic(self):

          #parse bus.config to find BU name 
          bus_config = os.path.join(os.path.dirname(conf.resource_base.rstrip(os.path.sep)),'bus.config')
          try:
              if os.path.exists(bus_config):
                  for line in open(bus_config,'r'):
                      if len(line):
                          return line.split('.')[0]
          except:
              pass
          return "unknown"

    def runESBox(self):

        #find out BU name
        self.logger.info("started ES box thread")
        if self.bu_mount_suffix:
          bu_name = self.bu_mount_suffix
        else:
          bu_name = self.getBUNameStatic()
        cpu_name,cpu_freq,self.cpu_cores,self.cpu_siblings = self.getCPUInfo()

        def refreshCPURange():
           num_cpus_new_real = self.testCPURange() 
           num_cpus_new = num_cpus_new_real * conf.dynamic_resources_multiplier 
           if num_cpus_new!=self.num_cpus:
             if conf.dynamic_resources and not conf.dqm_machine:
               self.state.lock.acquire()
               #notify run ranger thread
               self.state.os_cpuconfig_change += (num_cpus_new-self.num_cpus)
               if self.allow_resource_notifications:
                 with open(os.path.join(conf.watch_directory,'resourceupdate'),'w') as fp:
                   pass
               else:
                 self.buffered_resource_notification = os.path.join(conf.watch_directory,'resourceupdate')
               self.num_cpus=num_cpus_new
               self.num_cpus_real = num_cpus_new_real
               self.state.lock.release()


        #set/refresh initial number of CPUs
        if self.num_cpus==-1:
          self.num_cpus = self.testCPURange()
        else:
          refreshCPURange()

        ts_old = time.time()
        if cpu_name.startswith('AMD') or 'Nehalem' in cpu_name: #detecting CERN OpenStack VM hardware (used only for testing)
          tsc_old=mperf_old=aperf_old=tsc_new=mperf_new=aperf_new=0
          has_turbo=False
        else:
          tsc_old,mperf_old,aperf_old=self.getIntelCPUPerfAvgs()
          has_turbo = True
        self.threadEventESBox.wait(1)
        if conf.use_elasticsearch:
            eb = elasticBandBU(conf,0,'',False,update_run_mapping=False,update_box_mapping=True)
        rc = 0
        counter=0
        while self.running:
            try:
                if not self.found_data_interfaces or (rc%10)==0:
                  #check mountpoints every 10 loops
                  try:
                    self.findMountInterfaces()
                  except:
                    pass

                #if self.bu_mount_suffix:
                #  bu_name = self.bu_mount_suffix.split('.')[0]

                #refresh CPU information (e.g. if HT setting changed)
                cpu_name,cpu_freq,self.cpu_cores,self.cpu_siblings = self.getCPUInfo()

                dirstat = os.statvfs('/')
                d_used = ((dirstat.f_blocks - dirstat.f_bavail)*dirstat.f_bsize)>>20
                d_total =  (dirstat.f_blocks*dirstat.f_bsize)>>20
                dirstat_var = os.statvfs('/var')
                d_used_var = ((dirstat_var.f_blocks - dirstat_var.f_bavail)*dirstat_var.f_bsize)>>20
                d_total_var =  (dirstat_var.f_blocks*dirstat_var.f_bsize)>>20
                meminfo = self.getMEMInfo()
                #convert to MB
                memtotal = meminfo['MemTotal'] >> 10
                memused = memtotal - ((meminfo['MemFree']+meminfo['Buffers']+meminfo['Cached']+meminfo['SReclaimable']) >> 10)
                self.mem_frac = float(memused)/memtotal
                netrates = self.getRatesMBs()
                self.data_in_MB = netrates[0]
                cpu_freq_avg = self.getCPUFreqInfo()

                #every interval check number of CPUs (and signal refresh if using dynamic resources)
                refreshCPURange()

                #check cpu counters to estimate "Turbo" frequency
                ts_new = time.time()
                if has_turbo:
                  tsc_new,mperf_new,aperf_new=self.getIntelCPUPerfAvgs()

                if self.num_cpus_real>0 and mperf_new-mperf_old>0 and ts_new-ts_old>0:
                  self.cpu_freq_avg_real = int((1.* (tsc_new-tsc_old))/self.num_cpus_real / 1000000 * (aperf_new-aperf_old) / (mperf_new-mperf_old) /(ts_new-ts_old))
                else:
                  self.cpu_freq_avg_real = 0
                #detect counter wrap
                if self.cpu_freq_avg_real > 100000:
                        try:
                          self.logger.warning('intel cpu perf wrap [tsc,aperf]: ' + str(tsc_new)   + ' ' + str(tsc_old)   + ' ' + str(aperf_new) + str(aperf_old))
                          self.logger.warning('intel cpu perf wrap [mperf,ts]: '  + str(mperf_new) + ' ' + str(mperf_old) + ' ' + str(ts_new) + ' ' + str(ts_old))
                        except:pass
                        self.cpu_freq_avg_real=0
                ts_old=ts_new
                tsc_old=tsc_new
                aperf_old=aperf_new
                mperf_old=mperf_new

                #cpu_freq_avg_real = self.getTurbostatInfo() 
                doc = {
                    "date":datetime.datetime.utcfromtimestamp(time.time()).isoformat(),
                    "appliance":bu_name,
                    "cpu_name":cpu_name,
                    "cpu_MHz_nominal":int(cpu_freq*1000),
                    "cpu_phys_cores":self.cpu_cores,
                    "cpu_hyperthreads":self.cpu_siblings,
                    "cpu_usage_frac":psutil.cpu_percent()*0.01,
                    "cloudState":self.getCloudState(),
                    "activeRunList":self.runList.getActiveRunNumbers(),
                    "usedDisk":d_used,
                    "totalDisk":d_total,
                    "diskOccupancy":d_used/(1.*d_total) if d_total>0 else 0.,
                    "usedDiskVar":d_used_var,
                    "totalDiskVar":d_total_var,
                    "diskVarOccupancy":d_used_var/(1.*d_total_var) if d_total_var>0 else 0.,
                    "memTotal":memtotal,
                    "memUsed":memused,
                    "memUsedFrac":self.mem_frac,
                    "dataNetIn":netrates[0],
                    "dataNetOut":netrates[1],
                    "cpu_MHz_avg":cpu_freq_avg,
                    "cpu_MHz_avg_real":self.cpu_freq_avg_real
                }
                    #TODO: disk traffic(iostat)
                    #see: http://stackoverflow.com/questions/1296703/getting-system-status-in-python
                if conf.use_elasticsearch:
                    eb.elasticize_fubox(doc)
            except Exception as ex:
                self.logger.exception(ex)
            try:
                self.threadEventESBox.wait(5)
                rc+=1
            except:
                self.logger.info("Interrupted ESBox thread - ending")
                break
        if conf.use_elasticsearch:
            eb.stopping=True
            eb.threadEvent.set()
            self.logger.info("deleting elasticBandBU")
            del eb


    def getCloudState(self):
        cloud_st = "off"
        if self.state.cloud_mode:
          if self.state.entering_cloud_mode: cloud_st="starting"
          elif self.state.exiting_cloud_mode:cloud_st="stopping"
          else: cloud_st="on"
        #elif self.state.resources_blocked_flag:
        #    cloud_st = "resourcesReleased"
        elif self.state.masked_resources:
            cloud_st = "resourcesMasked"
        else:
            cloud_st = "off"
        return cloud_st


    def stop(self):
        self.logger.debug("request to stop")
        self.running = False
        self.threadEvent.set()
        self.threadEventStat.set()
        self.threadEventESBox.set()
        if self.statThread:
            self.statThread.join()
        if self.esBoxThread:
            self.esBoxThread.join()
        try:
            self.join()
        except:pass


