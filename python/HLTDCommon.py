import os
import sys
import json
import subprocess
import logging
import shutil

import demote
import prctl
from signal import SIGKILL

dqm_globalrun_filepattern = '.run{0}.global'

def restartLogCollector(conf,logger,logCollector,instanceParam):
    if logCollector!=None:
        logger.info("terminating logCollector")
        logCollector.terminate()
        logCollector = None
    logger.info("starting logcollector.py")
    logcollector_args = ['/opt/hltd/scratch/python/logcollector.py']
    logcollector_args.append(instanceParam)
    global user
    user = conf.user
    logCollector = subprocess.Popen(logcollector_args,preexec_fn=preexec_function,close_fds=True)

def preexec_function():
    dem = demote.demote(user)
    dem()
    prctl.set_pdeathsig(SIGKILL)
    #    os.setpgrp()

def updateFUListOnBU(conf,logger,lfilein,listname):

    lfiles = [lfilein] if lfilein else []
    if getattr(conf,'static_'+listname):
        lfiles.append('/etc/appliance/'+listname)
        logger.warning('using static '+listname+' file: '+lfiles[-1])
    fu_list=[]
    active_fu_list=[]
    success=False
    for lfile in lfiles:
      try:
        if os.stat(lfile).st_size>0:
            with open(lfile,'r') as fi:
                try:
                    static_fu_list = json.load(fi)
                    for item in static_fu_list:
                        fu_list.append(item)
                    logger.info("found these resources in " + lfile + " : " + str(fu_list))
                except ValueError:
                    logger.error("error parsing" + lfile)
      except:
        #no fu file, this is ok
        pass
    fu_list=list(set(fu_list))
    workdir_file = os.path.join(conf.watch_directory,'appliance',listname)
    try:
        with open(workdir_file,'r') as fi:
            active_fu_list = json.load(fi)
            success=True
    except:pass
    finally:
        if not success or active_fu_list != fu_list:
            try:
                with open(workdir_file,'w') as fi:
                    json.dump(fu_list,fi)
                    success=True
            except Exception as ex:
                logger.exception(ex)
    #TODO:check on FU if it is blacklisted or whitelisted

    #make a backup copy on local drive of last blacklist used
    try:
      shutil.copy(os.path.join(conf.watch_directory,'appliance',listname),os.path.join('/var/cache/hltd',listname+".last"))
    except:
      pass
    return success,fu_list

def restoreFUListOnBU(conf,logger,listname):
    if getattr(conf,'static_'+listname):
        logger.info('static '+listname+' used')
        return []
    dest = os.path.join(conf.watch_directory,'appliance',listname)
    try:
        shutil.copy(os.path.join('/var/cache/hltd',listname+".last"),dest)
    except:
        return []
    try:
        with open(dest,'r') as fi:
            ret = fi.read()
            retj =  json.loads(ret)
            logger.info('restoring '+listname+' from backup: '+ ret)
            return retj
    except Exception as ex:
        logger.info(dest + ' could not be read: ' + str(ex))
        return []

def deleteFUListOnBU(lfilein,listname):
    #resets (deletes) active blacklist and backup
    try:
        os.remove(lfilein)
    except:
        pass
    try:
        os.remove(os.path.join('/var/cache/hltd',listname+".last"))
    except:
        pass

def releaseLock(parent,lock,doLock=True,maybe=False,acqStatus=-1):
  if not doLock: return None
  if maybe:
    if not lock.locked(): return True #not locked anymore
  try:
    return lock.release()
  except RuntimeError as ex:
    import inspect
    if sys.version_info.major==3 and sys.version_info.minor>=5:
       funcname = inspect.stack()[1].function
    else:
      funcname = inspect.stack()[1][3]
    acq = "not provided" if acqStatus==-1 else str(acqStatus)
    parent.logger.warning("Failed unlocking lock in " + funcname + "/" + parent.__class__.__name__+". Acquire status was  "+acq+". Exception:"+str(ex))
    return None


def get_gdb_pids(in_pid):
    if not str(in_pid).isdigit(): return []
    p = subprocess.Popen("ps aux | grep 'gdb -quiet -p "+str(in_pid)+"' | grep -v grep | tr ' ' ' ' | cut -d' ' -f2",shell=True,stdout=subprocess.PIPE)
    x = [ int(y) for y in p.communicate()[0].decode('utf-8').strip('\n').split('\n') if y.isdigit()]
    return x

def kill_pids(in_pids):
    if not len(in_pids):return
    in_pids_filtered = []
    for pid in in_pids:
      s_pid = str(pid)
      if s_pid.isdigit():in_pids_filtered.append(s_pid)
    p = subprocess.Popen("/usr/bin/killall -9 "+" ".join(in_pids_filtered),stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    ret = p.communicate()
    if p.returncode:
        logging.info(ret[1].decode('utf-8').replace('\n','   '))

#find and kill
def clear_gdb_for_pid(in_pid):
  kill_pids(get_gdb_pids(in_pid))

