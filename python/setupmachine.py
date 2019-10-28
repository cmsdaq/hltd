#!/bin/env python
from __future__ import print_function

import os,sys,socket
import shutil
import json
import subprocess
import shutil
import syslog
import time

sys.path.append('/opt/hltd/python')

#for testing enviroment
try:
    import cx_Oracle
except ImportError:
    pass

backup_dir = '/opt/fff/backup'
try:
    os.makedirs(backup_dir)
except:pass

hltdconftemplate = '/etc/hltd.conf.template'
hltdconf = '/etc/hltd.conf'
busconfig = '/etc/appliance/bus.config'
cnhostname = ''

cred=None
dbsid = 'empty'
dblogin = 'empty'
dbpwd = 'empty'
equipmentSet = 'latest'
minidaq_list = ["bu-c2f13-14-01","bu-c2f13-16-01","bu-c2f13-25-01","bu-c2f13-27-01",
                "bu-c2f13-37-01","bu-c2f13-39-01","fu-c2f13-09-01","fu-c2f13-09-02","fu-c2f13-09-03",
                "fu-c2f13-20-01","fu-c2f13-20-02","fu-c2f13-20-03","fu-c2f13-33-01","fu-c2f13-33-02","bu-c2f13-41-01","bu-c2f13-29-01",
                "bu-c2e31-11-01","fu-c2e31-13-01"]
dqm_list     = ["bu-c2f11-09-01",
                "fu-c2f11-11-01","fu-c2f11-11-02","fu-c2f11-11-03","fu-c2f11-11-04"]
dqmtest_list = ["bu-c2f11-13-01",
                "fu-c2f11-15-01","fu-c2f11-15-02","fu-c2f11-15-03","fu-c2f11-15-04"]
detdqm_list  = ["bu-c2f11-19-01",
                "fu-c2f11-21-01","fu-c2f11-21-02","fu-c2f11-21-03","fu-c2f11-21-04",
                "fu-c2f11-23-01","fu-c2f11-23-02","fu-c2f11-23-03","fu-c2f11-23-04"]

es_cdaq_list = ['ncsrv-c2e42-09-02', 'ncsrv-c2e42-11-02', 'ncsrv-c2e42-13-02', 'ncsrv-c2e42-19-02']
es_local_list =[ 'ncsrv-c2e42-21-02', 'ncsrv-c2e42-23-02', 'ncsrv-c2e42-13-03', 'ncsrv-c2e42-23-03']

myhost = os.uname()[1]
try:myhost_domain = socket.getfqdn(myhost).split('.')[1]
except:myhost_domain=''

#testing dual mount point
vm_override_buHNs = {
                     "fu-vm-01-01.cern.ch":["bu-vm-01-01","bu-vm-01-01"],
                     "fu-vm-01-02.cern.ch":["bu-vm-01-01"],
                     "fu-vm-02-01.cern.ch":["bu-vm-01-01","bu-vm-01-01"],
                     "fu-vm-02-02.cern.ch":["bu-vm-01-01"],
                     "fu-vm-03-01.cern.ch":["bu-vm-03-01"],
                     "fu-vm-03-02.cern.ch":["bu-vm-03-01"],
                     "fu-vm-03-03.cern.ch":["bu-vm-03-01"],
                     "fu-vm-03-04.cern.ch":["bu-vm-03-01"]
                     }
#vm_bu_override = ['bu-vm-01-01.cern.ch']

#NOTE: DAQ2 tag will change when DB is updated to generate a new tag

def getmachinetype():

    #print "running on host ",myhost
    if myhost.startswith('dvrubu-') or myhost.startswith('dvfu-'):
      return 'daq2val',"fu"
    elif myhost.startswith('dvbu-') :
      return 'daq2val','bu'
    elif myhost.startswith('d3vfu-') :
      return 'daq3val','fu'
    elif myhost.startswith('d3vrubu-') :
      return 'daq3val','bu'
    elif myhost.startswith('fu-') and myhost_domain=='cms904': return 'daq2_904','fu'
    elif myhost.startswith('bu-') and myhost_domain=='cms904': return 'daq2_904','bu'
    elif myhost.startswith('fu-') : return 'daq2','fu'
    elif myhost.startswith('hilton-') : return 'hilton','fu'
    elif myhost.startswith('bu-') : return 'daq2','bu'
    elif myhost.startswith('cc7-ws'): return 'daq2','bu' #TESTING
    else:
        print("unknown machine type")
        return 'unknown','unknown'


def getIPs(hostname):
    try:
        ips = socket.gethostbyname_ex(hostname)
    except socket.gaierror as ex:
        print('unable to get ',hostname,'IP address:',str(ex))
        raise ex
    return ips

def getTimeString():
    tzones = time.tzname
    if len(tzones)>1:zone=str(tzones[1])
    else:zone=str(tzones[0])
    return str(time.strftime("%H:%M:%S"))+" "+time.strftime("%d-%b-%Y")+" "+zone


def checkModifiedConfigInFile(file):

    f = open(file)
    lines = f.readlines(2)#read first 2
    f.close()
    tzones = time.tzname
    if len(tzones)>1:zone=tzones[1]
    else:zone=tzones[0]

    for l in lines:
        if l.strip().startswith("#edited by fff meta rpm"):
            return True
    return False



def checkModifiedConfig(lines):
    for l in lines:
        if l.strip().startswith("#edited by fff meta rpm"):
            return True
    return False


#alternates between two data inteface indices based on host naming convention
def name_identifier():
    try:
        nameParts = os.uname()[1].split('-')
        return (int(nameParts[-1]) * int(nameParts[-2]//2)) % 2
    except:
        return 0

def setupDirsFU(fu_dir):
    #prepare and set permissions for the watch directory on FU
    try:
        os.umask(0)
        os.makedirs(fu_dir)
    except OSError:
        try:
            os.chmod(fu_dir,0o777)
        except:
            pass

def setupDirsBU(bu_dir):
    #ramdisk should already be present, but create subdirectory where hltd will write resource file
    try:
        os.umask(0)
        os.makedirs(bu_dir+'/appliance')
    except OSError:
        try:
            os.chmod(bu_dir+'/appliance',0o777)
        except:
            pass


def getBUAddr(parentTag,hostname,env_,eqset_,dblogin_,dbpwd_,dbsid_,retry=True):

    retval = []
    if env_ == "vm":
        try:
            #cluster in openstack that is not (yet) in mysql
            for bu_hn in vm_override_buHNs[hostname]:
                retval.append(["myBU",bu_hn])
        except:pass
        return retval

    try:
        session_suffix = hostname.split('-')[0]+hostname.split('-')[1]
        if parentTag == 'daq2':
            con = cx_Oracle.connect(dblogin_,dbpwd_,dbsid_,
                          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
        elif parentTag == 'daq2_904':
            con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_R',dbpwd_,'int2r_lb',
                          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
        else: #daq2val,daq3val
            con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_R',dbpwd_,'int2r_lb',
                          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)

    except Exception as ex:
        syslog.syslog('setupmachine.py: '+ str(ex))
        time.sleep(0.1)
        if retry:
            return getBUAddr(parentTag,hostname,env_,eqset_,dblogin_,dbpwd_,dbsid_,retry=False)
        else:
            raise ex
    #print con.version

    cur = con.cursor()

    #IMPORTANT: first query requires uppercase parent eq, while the latter requires lowercase eqset_

    qstring=  "select attr_name, attr_value from \
                DAQ_EQCFG_HOST_ATTRIBUTE ha, \
                DAQ_EQCFG_HOST_NIC hn, \
                DAQ_EQCFG_DNSNAME d \
                where \
                ha.eqset_id=hn.eqset_id AND \
                hn.eqset_id=d.eqset_id AND \
                ha.host_id = hn.host_id AND \
                ha.attr_name like 'myBU!_%' escape '!' AND \
                hn.nic_id = d.nic_id AND \
                d.dnsname = '" + hostname + "' \
                AND d.eqset_id = (select eqset_id from DAQ_EQCFG_EQSET \
                where tag='"+parentTag.upper()+"' AND \
                ctime = (SELECT MAX(CTIME) FROM DAQ_EQCFG_EQSET WHERE tag='"+parentTag.upper()+"')) order by attr_name"

    qstring2= "select attr_name, attr_value from \
                DAQ_EQCFG_HOST_ATTRIBUTE ha, \
                DAQ_EQCFG_HOST_NIC hn, \
                DAQ_EQCFG_DNSNAME d \
                where \
                ha.eqset_id=hn.eqset_id AND \
                hn.eqset_id=d.eqset_id AND \
                ha.host_id = hn.host_id AND \
                ha.attr_name like 'myBU!_%' escape '!' AND \
                hn.nic_id = d.nic_id AND \
                d.dnsname = '" + hostname + "' \
                AND d.eqset_id = (select eqset_id from DAQ_EQCFG_EQSET WHERE tag='"+parentTag.upper()+"' and cfgkey = '"+ eqset_ + "')"
                #AND d.eqset_id = (select child.eqset_id from DAQ_EQCFG_EQSET child, DAQ_EQCFG_EQSET \
                #parent WHERE child.parent_id = parent.eqset_id AND parent.cfgkey = '"+parentTag+"' and child.cfgkey = '"+ eqset_ + "')"

    #NOTE: to query squid master for the FU, replace 'myBU%' with 'mySquidMaster%'

    if eqset_ == 'latest':
        cur.execute(qstring)
    else:
        print("query equipment set",parentTag+'/'+eqset_)
        cur.execute(qstring2)

    retval = []
    for res in cur:
        retval.append(res)
    cur.close()
    con.close()
    if len(retval)==0:
        print('warning: query did not find anu BU for this FU')
        syslog.syslog('warning: query did not find anu BU for this FU')
    #print retval
    return retval

def countBU_FUs(parentTag,hostname,env_,eqset_,dblogin_,dbpwd_,dbsid_,retry=True):

    fu_count=0
    if env_ == "vm":
        for fu_hn in vm_override_buHNs:
            if vm_override_buHNs[fu_hn][0].strip('.')==hostname.strip('.')[0]:
                fu_count+=1
        return fu_count
    try:
        session_suffix = hostname.split('-')[0]+hostname.split('-')[1]
        if parentTag == 'daq2':
            con = cx_Oracle.connect(dblogin_,dbpwd_,dbsid_,
                          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
        elif parentTag == 'daq2_904':
            con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_R',dbpwd_,'int2r_lb',
                          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
        else: #daq2val,daq3val
            con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_R',dbpwd_,'int2r_lb',
                          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)

    except Exception as ex:
        syslog.syslog('setupmachine.py: '+ str(ex))
        return 0

    cur = con.cursor()

    qstring = "select d.dnsname from \
               DAQ_EQCFG_HOST_ATTRIBUTE ha, \
               DAQ_EQCFG_HOST_NIC hn, \
               DAQ_EQCFG_DNSNAME d \
               where \
               ha.eqset_id=hn.eqset_id AND \
               hn.eqset_id=d.eqset_id AND \
               ha.host_id = hn.host_id AND \
               ha.attr_name like 'myBU' AND \
               ha.attr_value = '"+hostname+"' AND \
               hn.nic_id = d.nic_id AND \
               (d.dnsname like '%fu-%' OR d.dnsname like '%d?vfu-%') AND \
               d.dnsname not like '%.%.cms' \
               AND d.eqset_id = (select eqset_id from DAQ_EQCFG_EQSET \
               where tag='"+parentTag.upper()+"' AND \
               ctime = (SELECT MAX(CTIME) FROM DAQ_EQCFG_EQSET WHERE tag='"+parentTag.upper()+"'))"

    cur.execute(qstring)
    for result in cur:
      fu_count+=1
    cur.close()
    con.close()
    return fu_count

#was used only for tribe:
#def getAllBU(requireFU=False):
#
#    #setups = ['daq2','daq2val']
#    parentTag = 'daq2'
#    if True:
#    #if parentTag == 'daq2':
#        if dbhost.strip()=='null':
#                #con = cx_Oracle.connect('CMS_DAQ2_HW_CONF_W','pwd','cms_rcms',
#            con = cx_Oracle.connect(dblogin,dbpwd,dbsid,
#                      cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
#        else:
#            con = cx_Oracle.connect(dblogin+'/'+dbpwd+'@'+dbhost+':10121/'+dbsid,
#                      cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
#    #else:
#    #    con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_W/'+dbpwd+'@int2r2-v.cern.ch:10121/int2r_lb.cern.ch',
#    #                  cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
#
#    cur = con.cursor()
#    retval = []
#    if requireFU==False:
#        qstring= "select dnsname from DAQ_EQCFG_DNSNAME where (dnsname like 'bu-%' OR dnsname like '__bu-%') \
#                  AND eqset_id = (select eqset_id from DAQ_EQCFG_EQSET where tag='"+parentTag.upper()+"' AND \
#                                  ctime = (SELECT MAX(CTIME) FROM DAQ_EQCFG_EQSET WHERE tag='"+parentTag.upper()+"'))"
#
#    else:
#        qstring = "select attr_value from \
#                        DAQ_EQCFG_HOST_ATTRIBUTE ha,       \
#                        DAQ_EQCFG_HOST_NIC hn,              \
#                        DAQ_EQCFG_DNSNAME d                  \
#                        where                                 \
#                        ha.eqset_id=hn.eqset_id AND            \
#                        hn.eqset_id=d.eqset_id AND              \
#                        ha.host_id = hn.host_id AND              \
#                        ha.attr_name like 'myBU!_%' escape '!' AND \
#                        hn.nic_id = d.nic_id AND                   \
#                        d.dnsname like 'fu-%'                       \
#                        AND d.eqset_id = (select eqset_id from DAQ_EQCFG_EQSET \
#                        where tag='"+parentTag.upper()+"' AND                    \
#                        ctime = (SELECT MAX(CTIME) FROM DAQ_EQCFG_EQSET WHERE tag='"+parentTag.upper()+"'))"
#
#
#
#def getSelfDataAddr(parentTag):
#
#
#    global equipmentSet
#    #con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_W/'+dbpwd+'@'+dbhost+':10121/int2r_lb.cern.ch',
#
#    con = cx_Oracle.connect(dblogin+'/'+dbpwd+'@'+dbhost+':10121/'+dbsid,
#                        cclass="FFFSETUP",purity = cx_Oracle.ATTR_PURITY_SELF)
#    #print con.version
#
#    cur = con.cursor()
#
#    hostname = os.uname()[1]
#
#    qstring1= "select dnsname from DAQ_EQCFG_DNSNAME where dnsname like '%"+os.uname()[1]+"%' \
#                AND d.eqset_id = (select child.eqset_id from DAQ_EQCFG_EQSET child, DAQ_EQCFG_EQSET \
#                parent WHERE child.parent_id = parent.eqset_id AND parent.cfgkey = '"+parentTag+"' and child.cfgkey = '"+ equipmentSet + "')"
#
#    qstring2 = "select dnsname from DAQ_EQCFG_DNSNAME where dnsname like '%"+os.uname()[1]+"%' \
#                AND eqset_id = (select child.eqset_id from DAQ_EQCFG_EQSET child, DAQ_EQCFG_EQSET parent \
#                WHERE child.parent_id = parent.eqset_id AND parent.cfgkey = '"+parentTag+"' and child.cfgkey = '"+ equipmentSet + "')"
#
#
#    if equipmentSet == 'latest':
#        cur.execute(qstring1)
#    else:
#        print "query equipment set (data network name): ",parentTag+'/'+equipmentSet
#        #print '\n',qstring2
#        cur.execute(qstring2)
#
#    retval = []
#    for res in cur:
#        if res[0] != os.uname()[1]+".cms": retval.append(res[0])
#    cur.close()
#
#    if len(retval)>1:
#        for r in res:
#            #prefer .daq2 network if available
#            if r.startswith(os.uname()[1]+'.daq2'): return [r]
#
#    return retval

def getInstances(hostname):
    #instance.input example:
    #{"cmsdaq-401b28.cern.ch":{"names":["main","ecal"],"sizes":[40,20]}} #size is in megabytes
    #BU can have multiple instances, FU should have only one specified. If none, any host is assumed to have only main instance
    try:
        with open('/opt/fff/instances.input','r') as fi:
            doc = json.load(fi)
            return doc[hostname]['names'],doc[hostname]['sizes']
    except:
        return ["main"],0


class FileManager:
    def __init__(self,file,templatefile,sep,edited,os1='',os2='',recreate=False):
        self.name = file
        if recreate==False:
            f = open(file if not templatefile else templatefile,'r')
            self.lines = f.readlines()
            f.close()
        else:
            self.lines=[]
        self.sep = sep
        self.regs = []
        self.remove = []
        self.edited = edited
        #for style
        self.os1=os1
        self.os2=os2

    def reg(self,key,val,section=None):
        self.regs.append([key,val,False,section])

    def removeEntry(self,key):
        self.remove.append(key)

    def commit(self):
        out = []
        #if self.edited  == False:
        out.append('#edited by fff meta rpm at '+getTimeString()+'\n')

        #first removing elements
        for rm in self.remove:
            for i,l in enumerate(self.lines):
                if l.strip().startswith(rm):
                    del self.lines[i]
                    break

        for i,l in enumerate(self.lines):
            lstrip = l.strip()
            if lstrip.startswith('#'):
                continue

            try:
                key = lstrip.split(self.sep)[0].strip()
                for r in self.regs:
                    if r[0] == key:
                        self.lines[i] = r[0].strip()+self.os1+self.sep+self.os2+r[1].strip()+'\n'
                        r[2]= True
                        break
            except:
                continue
        for r in self.regs:
            if r[2] == False:
                toAdd = r[0]+self.os1+self.sep+self.os2+r[1]+'\n'
                insertionDone = False
                if r[3] is not None:
                    for idx,l in enumerate(self.lines):
                        if l.strip().startswith(r[3]):
                            try:
                                self.lines.insert(idx+1,toAdd)
                                insertionDone = True
                            except:
                                pass
                            break
                if insertionDone == False:
                    self.lines.append(toAdd)
        for l in self.lines:
            #already written
            if l.startswith("#edited by fff meta rpm"):continue
            out.append(l)
        #print "file ",self.name,"\n\n"
        #for o in out: print o
        f = open(self.name,'w+')
        f.writelines(out)
        f.close()


def restoreFileMaybe(file):
    try:
        try:
            f = open(file,'r')
            lines = f.readlines()
            f.close()
            shouldCopy = checkModifiedConfig(lines)
        except:
            #backup also if file got deleted
            shouldCopy = True

        if shouldCopy:
            print("restoring ",file)
            backuppath = os.path.join(backup_dir,os.path.basename(file))
            f = open(backuppath)
            blines = f.readlines()
            f.close()
            if  checkModifiedConfig(blines) == False and len(blines)>0:
                shutil.move(backuppath,file)
    except Exception as ex:
        print("restoring problem: " , ex)
        pass

#main function
if __name__ == "__main__":
    if not len(sys.argv)>1 or sys.argv[1] not in ['configure','forceConfigure','disable','getrole','changeoption','setbusconfig']:
        print("Command parameter is missing or not among [configure,disable,getrole]")
        sys.exit(1)

    selection = sys.argv[1]
    #print selection

    if 'getrole' == selection:
        cluster,mtype = getmachinetype()
        print(mtype)
        sys.exit(0)

    elif 'disable' == selection:
        print("disabling hltd")
        hltdcfg = FileManager(hltdconf,hltdconftemplate,'=',True,' ',' ')
        hltdcfg.reg('enabled','False','[General]')
        hltdcfg.commit()
        sys.exit(0)
    elif 'changeoption' == selection:
      hltdcfg = FileManager(hltdconf,None,'=',True,' ',' ',recreate=False)
      section_str = sys.argv[4]
      if not section_str.startswith('['): section_str='['+section_str
      if not section_str.endswith(']'): section_str=section_str+']'
      par_val = sys.argv[3]
      if par_val=='true': par_val='True'
      if par_val=='false': par_val='False'
      hltdcfg.reg(sys.argv[2],par_val,section_str)
      hltdcfg.commit()
      sys.exit(0)
    elif 'setbusconfig' == selection:
      #note: this doesn't change dynamic_mounts option
      with open(busconfig,'w+') as f:
        f.writelines([sys.argv[2]])
      sys.exit(0)
 
    #else: configure or forceConfigure

    with open('/opt/fff/db.jsn','r') as fi:
        cred = json.load(fi)

    if 'env' not in cred:
        print("Enviroment parameter missing")
        sys.exit(1)
    env = cred['env']
    tmphost = os.uname()[1]

    #override environment for certain hostnames if "prod" detected:
    if tmphost.startswith("fu-vm-") or tmphost.startswith("bu-vm-") or tmphost.startswith('cc7-ws') and env=="prod":
      env="vm"
      cred = {
        "env":"vm",
        "revsuffix":"",
        "centrales":"es-vm-cdaq-01.cern.ch",
        "locales":"es-vm-local-01.cern.ch",
        "eqset":"test",
        "cmsswbase":"/home/daqlocal",
        "user":"daqlocal",
        "nthreads":"2",
        "nfwkstreams":"2",
        "cmsswloglevel":"INFO",
        "hltdloglevel":"ERROR",
        "login":"null",
        "password":"null",
        "sid":"null"
      }

    if 'centrales' not in cred:
        print("elasticsearch central host/alias missing")
        sys.exit(1)
    elastic_host = cred['centrales']
    elastic_host_url = 'http://'+elastic_host+':9200'

    if 'locales' not in cred:
        print("elasticsearch local host/alias missing")
        sys.exit(1)
    elastic_host_local = cred['locales']
    elastic_host_local_url = 'http://'+elastic_host_local+':9200'

    dbsid=cred['sid']
    dblogin=cred['login']
    dbpwd=cred['password']

    if 'eqset' not in cred:
        print("equipment set name missing")
        sys.exit(1)
    eqset_tmp = cred['eqset'].strip() 
    if eqset_tmp != '':
        equipmentSet = eqset_tmp

    if 'cmsswbase' not in cred:
        print("CMSSW base dist path missing")
        sys.exit(1)
    cmssw_base = cred['cmsswbase']

    if 'user' not in cred:
        print("CMSSW job username parameter is missing")
        sys.exit(1)
    username = cred['user']

    if 'nthreads' not in cred:
        print("CMSSW number of threads/process is missing")
        sys.exit(1)
    nthreads = cred['nthreads']
    #@SM: override
    #nthreads = 4
    resource_cmsswthreads = nthreads

    if 'nfwkstreams' not in cred:
        print("CMSSW number of framework streams/process is missing")
        sys.exit(1)
    nfwkstreams = cred['nfwkstreams']
     #@SM: override
    #nfwkstreams = 4
    resource_cmsswstreams = nfwkstreams

    if 'cmsswloglevel' not in cred:
        print("CMSSW log collection level is missing")
        sys.exit(1)
    cmsswloglevel = cred['cmsswloglevel']

    if 'hltdloglevel'not in cred:
        print("hltd log collection level is missing")
        sys.exit(1)
    hltdloglevel =  cred['hltdloglevel']

    #end of parameter parsing ----

    #override for daq2val!
    #if cluster == 'daq2val': cmsswloglevel =  'INFO'
    if env == "vm":
        cnhostname = os.uname()[1]
    else:
        cnhostname = os.uname()[1]+'.'+myhost_domain

    cluster,mtype = getmachinetype()

    isHilton = (cluster == "hilton")

    use_elasticsearch = 'True'
    cmssw_version = 'CMSSW_7_1_4_patch1' #stub
    dqmmachine = 'False'
    execdir = '/opt/hltd'
    auto_clear_quarantined = 'False'
    process_restart_limit = 1
    if resource_cmsswthreads == 1 or resource_cmsswstreams == 1:
        resourcefract = 0.33
        resourcefractd = 0.45
    else:
        resourcefract = 1
        resourcefractd = 1

    if cluster == 'daq2val':
        runindex_name = 'dv'
        auto_clear_quarantined = 'True'
    elif cluster == 'daq3val':
        runindex_name = 'd3v'
        auto_clear_quarantined = 'True'
    elif cluster == 'daq2':
        runindex_name = 'cdaq'
        if myhost in minidaq_list:
            runindex_name = 'minidaq'
            resourcefract = 1
            resourcefractd = 1
            resource_cmsswthreads = 1
            resource_cmsswstreams = 1
            #auto_clear_quarantined = 'True'
        if myhost in dqm_list or myhost in dqmtest_list or myhost in detdqm_list:
            process_restart_limit = 5
            use_elasticsearch = 'False'
            runindex_name = 'dqm'
            cmsswloglevel = 'DISABLED'
            dqmmachine = 'True'
            username = 'dqmpro'
            resourcefract = '1.0'
            resourcefractd = '1.0'
            resource_cmsswthreads = 1
            resource_cmsswstreams = 1
            cmssw_version = ''
            auto_clear_quarantined = 'True'
            if mtype == 'fu':
                cmsswloglevel = 'ERROR'
                cmssw_base = '/home/dqmprolocal'
                execdir = '/home/dqmprolocal/output' ##not yet
        if myhost in dqmtest_list:
            auto_clear_quarantined = 'False'
            runindex_name = 'dqmtest'
            username = 'dqmdev'
            if mtype == 'fu':
                cmsswloglevel = 'ERROR'
                cmssw_base = '/home/dqmdevlocal'
                execdir = '/home/dqmdevlocal/output' ##not yet
    elif cluster == 'daq2_904':
        runindex_name = 'b904'
        use_elasticsearch = 'False'
        elastic_host_url = 'http://localhost:9200' #will be changed in future
    elif isHilton:
        runindex_name = 'dv'
        use_elasticsearch = 'False'
        elastic_host_url = 'http://localhost:9200'

    buName = None
    buDataAddr=[]
    num_cfgdb_fus = 0
    bu_check_err = False

    if mtype == 'fu':
        if cluster in ['daq2val','daq3val','daq2','daq2_904']:
            for addr in getBUAddr(cluster,cnhostname,env,equipmentSet,dblogin,dbpwd,dbsid):
                if buName == None:
                    if isinstance(addr[1],str):
                      if len(addr[1])==0:
                        print("BU interface name is empty!")
                        continue
                      buName = addr[1].split('.')[0]
                    #this probably shouldn't happen
                    if buName == None:
                        msg = "no BU found for this FU in the dabatase. Setting dynamic mounts mode."
                        print(msg)
                        syslog.syslog(msg)
                        break
                elif buName != addr[1].split('.')[0]:
                    print("BU name not same for all interfaces:",buName,addr[1].split('.')[0])
                    bu_check_err = True
                    break
                #add to list
                buDataAddr.append(addr[1])

        elif not isHilton:
            print("FU configuration in cluster",cluster,"not supported yet !")
            sys.exit(-2)

    elif mtype == 'bu':
        buName = os.uname()[1].split(".")[0]
        #find out if any FUs are configured to this machine (statically)
        if cluster in ['daq2val','daq3val','daq2','daq2_904']:
            num_cfgdb_fus = countBU_FUs(cluster,cnhostname,env,equipmentSet,dblogin,dbpwd,dbsid)

    print("running configuration for machine",cnhostname,"of type",mtype,"in cluster",cluster,"; appliance bu is:",buName)

    hltdEdited = checkModifiedConfigInFile(hltdconf)
    if hltdEdited == False:
        shutil.copy(hltdconf,os.path.join(backup_dir,os.path.basename(hltdconf)))

    ###############################################################################

    if mtype=='bu':
            watch_dir_bu = '/fff/ramdisk'
            #out_dir_bu = '/fff/output'
            log_dir_bu = '/var/log/hltd'

            #FU should have one instance assigned, BUs can have multiple
            instances,sizes=getInstances(os.uname()[1])
            if len(instances)==0: instances=['main']

            try:os.remove('/etc/hltd.instances')
            except:pass

            #do major ramdisk cleanup (unmount existing loop mount points, run directories and img files)
            try:
                subprocess.check_call(['/opt/hltd/scripts/unmountloopfs.sh',watch_dir_bu])
                #delete existing run directories to ensure there is space (if this machine has a non-main instance)
                if instances!=["main"]:
                    os.popen('rm -rf /fff/ramdisk/run*')
            except subprocess.CalledProcessError as err1:
                print('failed to cleanup ramdisk',err1)
            except Exception as ex:
                print('failed to cleanup ramdisk',ex)

            cgibase=9000

            for idx,val in enumerate(instances):
                if idx!=0 and val=='main':
                    instances[idx]=instances[0]
                    instances[0]=val
                    break
            for idx, instance in enumerate(instances):

                watch_dir_bu_inst = watch_dir_bu
                log_dir_bu_inst = '/var/log/hltd'

                cfile = hltdconf
                if instance != 'main':
                    cfile = '/etc/hltd-'+instance+'.conf'
                    shutil.copy(hltdconf,cfile)
                    watch_dir_bu_inst = os.path.join(watch_dir_bu_inst,instance)
                    log_dir_bu_inst = os.path.join(log_dir_bu,instance)

                    #run loopback setup for non-main instances (is done on every boot since ramdisk is volatile)
                    try:
                        subprocess.check_call(['/opt/hltd/scripts/makeloopfs.sh', watch_dir_bu_inst, instance, str(sizes[idx])])
                    except subprocess.CalledProcessError as err1:
                        print('failed to configure loopback device mount in ramdisk')

                soap2file_port='0'

                if myhost in dqm_list or myhost in dqmtest_list or myhost in detdqm_list or cluster in ['daq2val','daq3val'] or env=='vm':
                    soap2file_port='8010'

                ################
                #write hltd.conf
                hltdcfg = FileManager(cfile,hltdconftemplate,'=',hltdEdited,' ',' ')

                hltdcfg.reg('enabled','True','[General]')
                hltdcfg.reg('role','bu','[General]')

                hltdcfg.reg('user',username,'[General]')
                hltdcfg.reg('instance',instance,'[General]')
                if num_cfgdb_fus==0 and dqmmachine=='False':
                  hltdcfg.reg('dynamic_mounts','True','[General]')

                #port for multiple instances
                hltdcfg.reg('cgi_port',str(cgibase+idx),'[Web]')
                hltdcfg.reg('cgi_instance_port_offset',str(idx),'[Web]')
                hltdcfg.reg('soap2file_port',soap2file_port,'[Web]')

                hltdcfg.reg('watch_directory',watch_dir_bu_inst,'[General]')
                if myhost in minidaq_list or cluster=='daq2_904' or dqmmachine=='True':
                  hltdcfg.reg('output_subdirectory_remote','output','[General]')
                if cluster=='daq3val': 
                  hltdcfg.reg('output_subdirectory_remote','ramdisk0','[General]')
                  hltdcfg.reg('drop_at_fu','True','[General]')
                  hltdcfg.reg('mon_bu_cpus','True','[Monitoring]')

                if cluster=='daq2val' or cluster=='daq3val':
                    hltdcfg.reg('static_blacklist','True','[General]')
                    hltdcfg.reg('static_whitelist','False','[General]') #!
                else:
                    hltdcfg.reg('static_blacklist','False','[General]')
                    hltdcfg.reg('static_whitelist','False','[General]')

                #hltdcfg.reg('micromerge_output',out_dir_bu,'[General]')
                hltdcfg.reg('elastic_runindex_url',elastic_host_url,'[Monitoring]')
                hltdcfg.reg('elastic_runindex_name',runindex_name,'[Monitoring]')
                hltdcfg.reg('es_local',elastic_host_local,'[Monitoring]')
                if env=='vm':
                    hltdcfg.reg('force_shards','2','[Monitoring]')
                    hltdcfg.reg('force_replicas','0','[Monitoring]')
                else:
                    hltdcfg.reg('force_shards','4','[Monitoring]')
                    hltdcfg.reg('force_replicas','1','[Monitoring]')
                hltdcfg.reg('use_elasticsearch',use_elasticsearch,'[Monitoring]')
                hltdcfg.reg('es_cmssw_log_level',cmsswloglevel,'[Monitoring]')
                hltdcfg.reg('es_hltd_log_level',hltdloglevel,'[Monitoring]')
                hltdcfg.reg('dqm_machine',dqmmachine,'[DQM]')
                hltdcfg.reg('log_dir',log_dir_bu_inst,'[Logs]')
                hltdcfg.commit()

                setupDirsBU(watch_dir_bu_inst)

            #write all instances in a file
            if 'main' not in instances or len(instances)>1:
                with open('/etc/hltd.instances',"w") as fi:
                    for instance in instances: fi.write(instance+"\n")

    if mtype=='fu':
            #first prepare bus.config file
            #try to remove old bus.config
            try:
              os.remove(os.path.join(backup_dir,os.path.basename(busconfig)))
            except:
              pass
            try:
              os.remove(busconfig)
            except:
              pass

            busconfig_used = True if (len(buDataAddr) or bu_check_err) else False 

            #write bu ip address
            if busconfig_used and not isHilton:
              with  open(busconfig,'w+') as f:
                #swap entries based on name (only C6100 hosts with two data interfaces):
                if len(buDataAddr)>1 and name_identifier()==1:
                    temp = buDataAddr[0]
                    buDataAddr[0]=buDataAddr[1]
                    buDataAddr[1]=temp

                newline=False
                for addr in buDataAddr:
                    if newline:f.writelines('\n')
                    newline=True
                    try:
                        nameToWrite = getIPs(addr)[0]
                    except Exception as ex:
                        print(ex)
                        #write bus.config even if name is not yet available by DNS
                        nameToWrite = addr
                    f.writelines(nameToWrite)


            ################
            #write hltd.conf

            hltdcfg = FileManager(hltdconf,hltdconftemplate,'=',hltdEdited,' ',' ')

            hltdcfg.reg('enabled','True','[General]')
            hltdcfg.reg('role','fu','[General]')

            hltdcfg.reg('user',username,'[General]')

            #FU can only have one instance (so we take instance[0] and ignore others)
            instances=['main']
            hltdcfg.reg('instance',instances[0],'[General]')

            if isHilton:
                hltdcfg.reg('bu_base_dir','/fff/BU0','[General]')

            #not set for Hilton, DQM and any setup not using NFS
            if  not busconfig_used and dqmmachine=='False':
                hltdcfg.reg('dynamic_mounts','True','[General]')

            hltdcfg.reg('exec_directory',execdir,'[General]')
            hltdcfg.reg('watch_directory','/fff/data','[General]')
            if myhost in minidaq_list or cluster=='daq2_904' or dqmmachine=='True':
              hltdcfg.reg('output_subdirectory_remote','output','[General]')
            if cluster=='daq3val':
              hltdcfg.reg('output_subdirectory_remote','ramdisk0','[General]')
              #hltdcfg.reg('drop_at_fu','True','[General]')

            hltdcfg.reg('static_blacklist','False','[General]')
            hltdcfg.reg('static_whitelist','False','[General]')
            hltdcfg.reg('cgi_port','9000','[Web]')
            hltdcfg.reg('cgi_instance_port_offset',"0",'[Web]')
            hltdcfg.reg('soap2file_port','0','[Web]')
            hltdcfg.reg('es_cmssw_log_level',cmsswloglevel,'[Monitoring]')
            hltdcfg.reg('es_hltd_log_level',hltdloglevel,'[Monitoring]')
            hltdcfg.reg('elastic_runindex_url',elastic_host_url,'[Monitoring]')
            hltdcfg.reg('elastic_runindex_name',runindex_name,'[Monitoring]')
            hltdcfg.reg('es_local',elastic_host_local,'[Monitoring]')
            if env=='vm':
                hltdcfg.reg('force_shards','2','[Monitoring]')
                hltdcfg.reg('force_replicas','0','[Monitoring]')
                hltdcfg.reg('dynamic_resources','False','[Resources]')
            else:
                hltdcfg.reg('force_shards','4','[Monitoring]')
                hltdcfg.reg('force_replicas','1','[Monitoring]')
            hltdcfg.reg('use_elasticsearch',use_elasticsearch,'[Monitoring]')
            hltdcfg.reg('dqm_machine',dqmmachine,'[DQM]')
            hltdcfg.reg('auto_clear_quarantined',auto_clear_quarantined,'[Recovery]')
            hltdcfg.reg('process_restart_limit',str(process_restart_limit),'[Recovery]')
            hltdcfg.reg('cmssw_base',cmssw_base,'[CMSSW]')
            hltdcfg.reg('cmssw_default_version',cmssw_version,'[CMSSW]')
            hltdcfg.reg('cmssw_threads',str(resource_cmsswthreads),'[CMSSW]')
            hltdcfg.reg('cmssw_streams',str(resource_cmsswstreams),'[CMSSW]')
            #if myhost.startswith('fu-c2d'):
            hltdcfg.reg('resource_use_fraction',str(resourcefractd),'[Resources]')
            #else:
            #    hltdcfg.reg('resource_use_fraction',str(resourcefract),'[Resources]')
            hltdcfg.commit()
            setupDirsFU('/fff/data')

    if 'forceConfigure' == selection:
        from fillresources import runFillResources
        runFillResources(force=True)

