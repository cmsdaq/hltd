#!/bin/env python

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
try:
    import MySQLdb
except ImportError:
    pass

backup_dir = '/opt/fff/backup'
try:
    os.makedirs(backup_dir)
except:pass

hltdconftemplate = '/etc/hltd.conf.template'
hltdconf = '/etc/hltd.conf'
busconfig = '/etc/appliance/bus.config'

dbhost = 'empty'
dbsid = 'empty'
dblogin = 'empty'
dbpwd = 'empty'
equipmentSet = 'latest'
minidaq_list = ["bu-c2f13-14-01","bu-c2f13-16-01","bu-c2f13-25-01","bu-c2f13-27-01",
                "bu-c2f13-37-01","bu-c2f13-39-01","fu-c2f13-09-01","fu-c2f13-09-02","fu-c2f13-09-03",
                "fu-c2f13-20-01","fu-c2f13-20-02","fu-c2f13-20-03","fu-c2f13-33-01","fu-c2f13-33-02","bu-c2f13-41-01","bu-c2f13-29-01"]
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


def getmachinetype():

    #print "running on host ",myhost
    if   myhost.startswith('dvrubu-') or myhost.startswith('dvfu-') : return 'daq2val','fu'
    elif myhost.startswith('dvbu-') : return 'daq2val','bu'
    elif myhost.startswith('fu-') and myhost_domain=='cms904': return 'daq2_904','fu'
    elif myhost.startswith('bu-') and myhost_domain=='cms904': return 'daq2_904','bu'
    elif myhost.startswith('fu-') : return 'daq2','fu'
    elif myhost.startswith('hilton-') : return 'hilton','fu'
    elif myhost.startswith('bu-') : return 'daq2','bu'
    else:
        print "unknown machine type"
        return 'unknown','unknown'


def getIPs(hostname):
    try:
        ips = socket.gethostbyname_ex(hostname)
    except socket.gaierror, ex:
        print 'unable to get ',hostname,'IP address:',str(ex)
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
        return (int(nameParts[-1]) * int(nameParts[-2]/2)) % 2
    except:
        return 0

def setupDirs(role,fu_dir,bu_dir):
    #prepare and set permissions for the watch directory on FU
    if role=='fu':
        try:
            os.umask(0)
            os.makedirs(fu_dir)
        except OSError:
            try:
                os.chmod(fu_dir,0777)
            except:
                pass

    elif role=='bu':
        #ramdisk should already be present, but create subdirectory where hltd will write resource file
        try:
            os.umask(0)
            os.makedirs(bu_dir+'/appliance')
        except OSError:
            try:
                os.chmod(bu_dir+'/appliance',0777)
            except:
                pass


def getBUAddr(parentTag,hostname,env_,eqset_,dbhost_,dblogin_,dbpwd_,dbsid_,retry=True):

    try:
        if env_ == "vm":
            try:
            #cluster in openstack that is not (yet) in mysql
                retval = []
                for bu_hn in vm_override_buHNs[hostname]:
                    retval.append(["myBU",bu_hn])
                return retval
            except:
                pass
            con = MySQLdb.connect( host= dbhost_, user = dblogin_, passwd = dbpwd_, db = dbsid_)
        else:
            session_suffix = hostname.split('-')[0]+hostname.split('-')[1]
            if parentTag == 'daq2':
                if dbhost_.strip()=='empty':
                #con = cx_Oracle.connect('CMS_DAQ2_HW_CONF_W','pwd','cms_rcms',
                    con = cx_Oracle.connect(dblogin_,dbpwd_,dbsid_,
                              cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
                else:
                    sys.exit(2)
                    #con = cx_Oracle.connect(dblogin_+'/'+dbpwd_+'@'+dbhost_+':10121/'+dbsid_,
                    #          cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
            elif parentTag == 'daq2_904':
                con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_R',dbpwd_,'int2r_lb',
                              cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)
            else: #daq2val
                con = cx_Oracle.connect('CMS_DAQ2_TEST_HW_CONF_R',dbpwd_,'int2r_lb',
                              cclass="FFFSETUP"+session_suffix,purity = cx_Oracle.ATTR_PURITY_SELF)

    except Exception as ex:
        syslog.syslog('setupmachine.py: '+ str(ex))
        time.sleep(0.1)
        if retry:
            return getBUAddr(parentTag,hostname,env_,eqset_,dbhost_,dblogin_,dbpwd_,dbsid_,retry=False)
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
        print "query equipment set",parentTag+'/'+eqset_
        cur.execute(qstring2)

    retval = []
    for res in cur:
        retval.append(res)
    cur.close()
    if len(retval)==0:
        print 'warning: query did not find anu BU for this FU'
        syslog.syslog('warning: query did not find anu BU for this FU')
    #print retval
    return retval

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
            print "restoring ",file
            backuppath = os.path.join(backup_dir,os.path.basename(file))
            f = open(backuppath)
            blines = f.readlines()
            f.close()
            if  checkModifiedConfig(blines) == False and len(blines)>0:
                shutil.move(backuppath,file)
    except Exception, ex:
        print "restoring problem: " , ex
        pass

#main function
if __name__ == "__main__":
    if not len(sys.argv)>1 or sys.argv[1] not in ['configure','forceConfigure','disable','getrole']:
        print "Command parameter is missing or not among [configure,disable,getrole]"
        sys.exit(1)

    selection = sys.argv[1]
    #print selection
    if 'getrole' == selection:
        cluster,mtype = getmachinetype()
        print mtype
        sys.exit(0)

    elif 'disable' == selection:
        print "disabling hltd"
        hltdcfg = FileManager(hltdconf,hltdconftemplate,'=',True,' ',' ')
        hltdcfg.reg('enabled','False','[General]')
        hltdcfg.commit()
        sys.exit(0)

    #else: configure or forceConfigure

    with open('/opt/fff/db.jsn','r') as fi:
        cred = json.load(fi)

    if 'env' not in cred:
        print "Enviroment parameter missing"
        sys.exit(1)
    env = cred['env']

    if 'centrales' not in cred:
        print "elasticsearch central host/alias missing"
        sys.exit(1)
    elastic_host = cred['centrales']
    elastic_host_url = 'http://'+elastic_host+':9200'

    if 'locales' not in cred:
        print "elasticsearch local host/alias missing"
        sys.exit(1)
    elastic_host_local = cred['locales']
    elastic_host_local_url = 'http://'+elastic_host_local+':9200'

    dbsid=cred['sid']
    dblogin=cred['login']
    dbpwd=cred['password']

    if 'eqset' not in cred:
        print "equipment set name missing"
        sys.exit(1)
    eqset_tmp = cred['eqset'].strip() 
    if eqset_tmp != '':
        equipmentSet = eqset_tmp

    if 'cmsswbase' not in cred:
        print "CMSSW base dist path missing"
        sys.exit(1)
    cmssw_base = cred['cmsswbase']

    if 'user' not in cred:
        print "CMSSW job username parameter is missing"
        sys.exit(1)
    username = cred['user']

    if 'nthreads' not in cred:
        print "CMSSW number of threads/process is missing"
        sys.exit(1)
    nthreads = cred['nthreads']
    #@SM: override
    #nthreads = 4
    resource_cmsswthreads = nthreads

    if 'nfwkstreams' not in cred:
        print "CMSSW number of framework streams/process is missing"
        sys.exit(1)
    nfwkstreams = cred['nfwkstreams']
     #@SM: override
    #nfwkstreams = 4
    resource_cmsswstreams = nfwkstreams

    if 'cmsswloglevel' not in cred:
        print "CMSSW log collection level is missing"
        sys.exit(1)
    cmsswloglevel = cred['cmsswloglevel']

    if 'hltdloglevel'not in cred:
        print "hltd log collection level is missing"
        sys.exit(1)
    hltdloglevel =  cred['hltdloglevel']

    #end of parameter parsing ----

    cluster,mtype = getmachinetype()
    #override for daq2val!
    #if cluster == 'daq2val': cmsswloglevel =  'INFO'
    if env == "vm":
        cnhostname = os.uname()[1]
    else:
        cnhostname = os.uname()[1]+'.'+myhost_domain

    use_elasticsearch = 'True'
    cmssw_version = 'CMSSW_7_1_4_patch1' #stub
    dqmmachine = 'False'
    execdir = '/opt/hltd'
    auto_clear_quarantined = 'False'
    if resource_cmsswthreads == 1 or resource_cmsswstreams == 1:
        resourcefract = 0.33
        resourcefractd = 0.45
    else:
        resourcefract = 1
        resourcefractd = 1

    if cluster == 'daq2val':
        runindex_name = 'dv'
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
    elif cluster == 'hilton':
        runindex_name = 'dv'
        use_elasticsearch = 'False'
        elastic_host_url = 'http://localhost:9200'

    buName = None
    buDataAddr=[]

    if mtype == 'fu':
        if cluster == 'daq2val' or cluster == 'daq2' or cluster == 'daq2_904':
            for addr in getBUAddr(cluster,cnhostname,env,equipmentSet,dbhost,dblogin,dbpwd,dbsid):
                if buName==None:
                    buName = addr[1].split('.')[0]
                elif buName != addr[1].split('.')[0]:
                    print "BU name not same for all interfaces:",buName,addr[1].split('.')[0]
                    continue
                buDataAddr.append(addr[1])
                #if none are pingable, first one is picked
                if buName == None or len(buDataAddr)==0:
                    print "no BU found for this FU in the dabatase"
                    syslog.syslog("no BU found for this FU in the database")
                    sys.exit(-1)
        elif cluster == 'hilton':
            pass
        else:
            print "FU configuration in cluster",cluster,"not supported yet !!"
            sys.exit(-2)

    elif mtype == 'bu':
        if env == "vm":
            buName = os.uname()[1].split(".")[0]
        else:
            buName = os.uname()[1]

    print "running configuration for machine",cnhostname,"of type",mtype,"in cluster",cluster,"; appliance bu is:",buName
    if buName==None: buName=""

    clusterName='appliance_'+buName

    if cluster=='hilton':
        clusterName='appliance_hilton'

    if True:

        #first prepare bus.config file
        if mtype == 'fu':

        #permissive:try to remove old bus.config
            try:os.remove(os.path.join(backup_dir,os.path.basename(busconfig)))
            except:pass
            try:os.remove(busconfig)
            except:pass

            #write bu ip address
            if cluster!='hilton':
                f = open(busconfig,'w+')
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
                        print ex
                        #write bus.config even if name is not yet available by DNS
                        nameToWrite = addr
                    f.writelines(nameToWrite)
                f.close()

        #FU should have one instance assigned, BUs can have multiple
        watch_dir_bu = '/fff/ramdisk'
        out_dir_bu = '/fff/output'
        log_dir_bu = '/var/log/hltd'

        instances,sizes=getInstances(os.uname()[1])
        if len(instances)==0: instances=['main']

        hltdEdited = checkModifiedConfigInFile(hltdconf)

        if hltdEdited == False:
            shutil.copy(hltdconf,os.path.join(backup_dir,os.path.basename(hltdconf)))

        if mtype=='bu':
            try:os.remove('/etc/hltd.instances')
            except:pass

            #do major ramdisk cleanup (unmount existing loop mount points, run directories and img files)
            try:
                subprocess.check_call(['/opt/hltd/scripts/unmountloopfs.sh','/fff/ramdisk'])
                #delete existing run directories to ensure there is space (if this machine has a non-main instance)
                if instances!=["main"]:
                    os.popen('rm -rf /fff/ramdisk/run*')
            except subprocess.CalledProcessError, err1:
                print 'failed to cleanup ramdisk',err1
            except Exception as ex:
                print 'failed to cleanup ramdisk',ex

            cgibase=9000

            for idx,val in enumerate(instances):
                if idx!=0 and val=='main':
                    instances[idx]=instances[0]
                    instances[0]=val
                    break
            for idx, instance in enumerate(instances):

                watch_dir_bu = '/fff/ramdisk'
                out_dir_bu = '/fff/output'
                log_dir_bu = '/var/log/hltd'

                cfile = hltdconf
                if instance != 'main':
                    cfile = '/etc/hltd-'+instance+'.conf'
                    shutil.copy(hltdconf,cfile)
                    watch_dir_bu = os.path.join(watch_dir_bu,instance)
                    out_dir_bu = os.path.join(out_dir_bu,instance)
                    log_dir_bu = os.path.join(log_dir_bu,instance)

                    #run loopback setup for non-main instances (is done on every boot since ramdisk is volatile)
                    try:
                        subprocess.check_call(['/opt/hltd/scripts/makeloopfs.sh','/fff/ramdisk',instance, str(sizes[idx])])
                    except subprocess.CalledProcessError, err1:
                        print 'failed to configure loopback device mount in ramdisk'

                soap2file_port='0'

                if myhost in dqm_list or myhost in dqmtest_list or myhost in detdqm_list or cluster == 'daq2val' or env=='vm':
                    soap2file_port='8010'

                hltdcfg = FileManager(cfile,hltdconftemplate,'=',hltdEdited,' ',' ')

                hltdcfg.reg('enabled','True','[General]')
                hltdcfg.reg('role','bu','[General]')

                hltdcfg.reg('user',username,'[General]')
                hltdcfg.reg('instance',instance,'[General]')

                #port for multiple instances
                hltdcfg.reg('cgi_port',str(cgibase+idx),'[Web]')
                hltdcfg.reg('cgi_instance_port_offset',str(idx),'[Web]')
                hltdcfg.reg('soap2file_port',soap2file_port,'[Web]')

                hltdcfg.reg('elastic_cluster',clusterName,'[Monitoring]')

                hltdcfg.reg('watch_directory',watch_dir_bu,'[General]')

                if cluster=='daq2val':
                    hltdcfg.reg('static_blacklist','True','[General]')
                else:
                    hltdcfg.reg('static_blacklist','False','[General]')

                #hltdcfg.reg('micromerge_output',out_dir_bu,'[General]')
                hltdcfg.reg('elastic_runindex_url',elastic_host_url,'[Monitoring]')
                hltdcfg.reg('elastic_runindex_name',runindex_name,'[Monitoring]')
                hltdcfg.reg('es_local',elastic_host_local,'[Monitoring]')
                if env=='vm':
                    hltdcfg.reg('force_replicas','0','[Monitoring]')
                else:
                    hltdcfg.reg('force_replicas','1','[Monitoring]')
                hltdcfg.reg('force_shards','4','[Monitoring]')
                hltdcfg.reg('use_elasticsearch',use_elasticsearch,'[Monitoring]')
                hltdcfg.reg('es_cmssw_log_level',cmsswloglevel,'[Monitoring]')
                hltdcfg.reg('es_hltd_log_level',hltdloglevel,'[Monitoring]')
                hltdcfg.reg('dqm_machine',dqmmachine,'[DQM]')
                hltdcfg.reg('log_dir',log_dir_bu,'[Logs]')
                hltdcfg.commit()

            #write all instances in a file
            if 'main' not in instances or len(instances)>1:
                with open('/etc/hltd.instances',"w") as fi:
                    for instance in instances: fi.write(instance+"\n")

        if mtype=='fu':
            hltdcfg = FileManager(hltdconf,hltdconftemplate,'=',hltdEdited,' ',' ')

            hltdcfg.reg('enabled','True','[General]')
            hltdcfg.reg('role','fu','[General]')

            hltdcfg.reg('user',username,'[General]')
            #FU can only have one instance (so we take instance[0] and ignore others)
            hltdcfg.reg('instance',instances[0],'[General]')
            if cluster=='hilton':
                hltdcfg.reg('bu_base_dir','/fff/BU0','[General]')

            hltdcfg.reg('exec_directory',execdir,'[General]')
            hltdcfg.reg('watch_directory','/fff/data','[General]')
            hltdcfg.reg('static_blacklist','False','[General]')
            hltdcfg.reg('cgi_port','9000','[Web]')
            hltdcfg.reg('cgi_instance_port_offset',"0",'[Web]')
            hltdcfg.reg('soap2file_port','0','[Web]')
            hltdcfg.reg('elastic_cluster',clusterName,'[Monitoring]')
            hltdcfg.reg('es_cmssw_log_level',cmsswloglevel,'[Monitoring]')
            hltdcfg.reg('es_hltd_log_level',hltdloglevel,'[Monitoring]')
            hltdcfg.reg('elastic_runindex_url',elastic_host_url,'[Monitoring]')
            hltdcfg.reg('elastic_runindex_name',runindex_name,'[Monitoring]')
            hltdcfg.reg('es_local',elastic_host_local,'[Monitoring]')
            if env=='vm':
                hltdcfg.reg('force_replicas','0','[Monitoring]')
                hltdcfg.reg('dynamic_resources','False','[Resources]')
            else:
                hltdcfg.reg('force_replicas','1','[Monitoring]')
            hltdcfg.reg('force_shards','4','[Monitoring]')
            hltdcfg.reg('use_elasticsearch',use_elasticsearch,'[Monitoring]')
            hltdcfg.reg('dqm_machine',dqmmachine,'[DQM]')
            hltdcfg.reg('auto_clear_quarantined',auto_clear_quarantined,'[Recovery]')
            hltdcfg.reg('cmssw_base',cmssw_base,'[CMSSW]')
            hltdcfg.reg('cmssw_default_version',cmssw_version,'[CMSSW]')
            hltdcfg.reg('cmssw_threads',str(resource_cmsswthreads),'[CMSSW]')
            hltdcfg.reg('cmssw_streams',str(resource_cmsswstreams),'[CMSSW]')
            #if myhost.startswith('fu-c2d'):
            hltdcfg.reg('resource_use_fraction',str(resourcefractd),'[Resources]')
            #else:
            #    hltdcfg.reg('resource_use_fraction',str(resourcefract),'[Resources]')
            hltdcfg.commit()

    setupDirs(mtype, '/fff/data',watch_dir_bu)
    if 'forceConfigure' == selection:
        from fillresources import runFillResources
        runFillResources(force=True)

