
from configparser import SafeConfigParser,RawConfigParser

import logging
import os
import datetime

class hltdConf:

        #autodetecting by name if role is not specified
    def __init__(self, conffile):

        cfg = SafeConfigParser()
        cfg.read(conffile)
        self.cfg=cfg
        self.paramlist = []
        self.parse_known_parameters()

        self.finish_init_parameters()
        #cleanup
        self.cfg=None


    def parse_known_parameters(self):

        #all values are parsed here
        #for sec in cfg.sections():
        #    for item,value in cfg.items(sec):
        #        self.__dict__[item] = value
        self.getbool('General','enabled',False)
        self.getstr('General','role',"None")
        self.getstr('General','instance','main')
        self.getstr('General','exec_directory','/opt/hltd')
        self.getstr('General','user','daqlocal')
        self.getbool('General','local_mode',False)
        self.getbool('General','dynamic_mounts',False)
        self.getstr('General','fff_base', "/fff")
        self.getstr('General','watch_directory', "None")
        self.getstr('General','bu_base_dir', "/fff/BU")
        self.getstr('General','bu_base_dir_autofs', "/fff/BUs")
        self.getstr('General','ramdisk_subdirectory', "ramdisk") #local mountpoint
        self.getstr('General','ramdisk_subdirectory_remote', "ramdisk") #remote or on BU
        self.getstr('General','output_subdirectory', "output") #local mountpoint
        self.getstr('General','output_subdirectory_remote', "output") #remote or on BU
        self.getstr('General','output_subdirectory_aux', "None") #final output directory (merger), if different
        self.getstr('General','data_subdirectory', "data")
        self.getint('General','run_number_padding',6)

        self.getstr('Mount','mount_command', "/usr/bin/mount")
        self.getstr('Mount','mount_options_ramdisk', 'rw,noatime,vers=4,rsize=65536,wsize=65536,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,lookupcache=positive')
        self.getstr('Mount','mount_options_output', 'rw,vers=4,rsize=65536,wsize=10485760,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,lookupcache=positive')

        #TESTING
        self.getbool('Test','output_adler32',True)
        self.getbool('Test','mount_control_path',False)
        self.getbool('Test','static_whitelist',False)
        self.getbool('Test','static_blacklist',False)
        self.getbool('Test','delete_run_dir',True)
        self.getbool('Test','drop_at_fu',False)
        self.getint('Test','fastmon_insert_modulo',1)
        self.getint('Test','dynamic_resources_multiplier',1)

        self.getbool('Monitoring','use_elasticsearch',False)
        self.getstr('Monitoring','es_cmssw_log_level',"DISABLED")
        self.getstr('Monitoring','es_hltd_log_level',"ERROR")
        self.getstr('Monitoring','es_cdaq', "localhost")
        self.getstr('Monitoring','es_local', "localhost")
        self.getstr('Monitoring','elastic_index_suffix',"cdaq")
        self.getint('Monitoring','force_replicas',-1)
        self.getint('Monitoring','force_shards',-1)
        self.getbool('Monitoring','update_es_template',True)
        self.getbool('Monitoring','mon_bu_cpus',False)

        self.getint('Web','cgi_port',9000)
        self.getint('Web','cgi_instance_port_offset',0)
        self.getint('Web','soap2file_port',8010)

        self.getstr('Resources','resource_base','/etc/appliance/resources')
        self.getfloat('Resources','resource_use_fraction',1)
        self.getint('Resources','max_local_disk_usage',2048)
        self.getbool('Resources','dynamic_resources',True)

        self.getbool('DQM','dqm_machine',False)
        self.getstr('DQM','dqm_resource_base',"/etc/appliance/dqm_resources")
        self.getbool('DQM','dqm_globallock',True)

        self.getfloat('Recovery','process_restart_delay_sec',5.)
        self.getint('Recovery','process_restart_limit',5)
        self.getbool('Recovery','auto_clear_quarantined',False)
        self.getIntVector('Recovery','auto_clear_exitcodes','0,127')

        self.getstr('CMSSW','cmssw_base',"/opt/offline")
        self.getstr('CMSSW','cmssw_arch',"notset")
        self.getstr('CMSSW','cmssw_default_version',"notset")
        self.getint('CMSSW','cmssw_threads_autosplit',0)
        self.getint('CMSSW','cmssw_threads',1)
        self.getint('CMSSW','cmssw_streams',1)
        self.getstr('CMSSW','cmssw_script_location',"/opt/hltd/scripts")
        self.getstr('CMSSW','test_hlt_config1',"python/HiltonMenu.py")
        self.getbool('CMSSW','detect_fasthadd_version',False)

        self.getstr('HLT','menu_directory',"hlt")
        self.getstr('HLT','menu_name',"HltConfig.py")
        self.getstr('HLT','paramfile_name',"fffParameters.jsn")
        self.getstr('HLT','hltinfofile_name',"hltinfo")

        self.getstr('Cloud','cloud_igniter_path',"/usr/local/sbin/cloud-igniter.py")

        self.getstr('Logs','service_log_level',"INFO")
        self.getstr('Logs','log_dir', "/var/log/hltd")

    def finish_init_parameters(self):

        self.service_log_level = getattr(logging,self.service_log_level)
        #DQM setting:
        if self.dqm_machine:
            self.resource_base = self.dqm_resource_base

        if self.role in [None,"None"]:
            if os.uname()[1].startswith('bu-') or os.uname()[1].startswith('dvbu-') or os.uname()[1].startswith('d3vrubu-'):
                self.role = 'bu'
            else:
                self.role = 'fu'
        if self.watch_directory in [None,"None"]:
            if self.role == 'bu': self.watch_directory=os.path.join(self.fff_base,self.ramdisk_subdirectory)
            if self.role == 'fu': self.watch_directory=os.path.join(self.fff_base,self.data_subdirectory)

    #helper members

    def getstr(self,section,name,default):
        try:
            setattr(self,name,self.cfg.get(section,name))
        except:
            setattr(self,name,default)
        self.paramlist.append([name,'str',default,section])
        #    logging.info('setting default '+ name + ' ' + str(default))

    def getbool(self,section,name,default):
        try:
            setattr(self,name,self.cfg.getboolean(section,name))
        except:
            setattr(self,name,default)
        self.paramlist.append([name,'bool',default,section])
        #    logging.info('setting default '+ name + ' ' + str(default))

    def getint(self,section,name,default):
        try:
            setattr(self,name,self.cfg.getint(section,name))
        except:
            setattr(self,name,default)
        self.paramlist.append([name,'int',default,section])
        #    logging.info('setting default '+ name + ' ' + str(default))

    def getfloat(self,section,name,default):
        try:
            setattr(self,name,self.cfg.getfloat(section,name))
        except:
            setattr(self,name,default)
        self.paramlist.append([name,'float',default,section])
        #    logging.info('setting default '+ name + ' ' + str(default))

    def dumpConfigToFile(self,path):
        tmpcfg = RawConfigParser()
        for p in self.paramlist:
            if not tmpcfg.has_section(p[3]):
                tmpcfg.add_section(p[3])
            if p[1]=='intvec' or p[1]=='strvec':
              tmpcfg.set(p[3],p[0],','.join(map(str,p[2])))
            else:
              tmpcfg.set(p[3],p[0],str(p[2]))
        with open(path,'w') as outfile:
            tmpcfg.write(outfile)

    def getStrVector(self,section,name,default):
        try:
            setattr(self,name,self.cfg.get(section,name).split(','))
        except:
            setattr(self,name,default.split(','))
        self.paramlist.append([name,'intvec',default,section])
 
    def getIntVector(self,section,name,default):
        try:
            setattr(self,name,[int(x) for x in self.cfg.get(section,name).split(',')])
        except:
            setattr(self,name,[int(x) for x in default.split(',')])
        self.paramlist.append([name,'intvec',default,section])
 
    def dump(self):
        logging.info( '<hltd STATUS time="' + str(datetime.datetime.now()).split('.')[0] + '" user:' + self.user + ' role:' + self.role + '>')



def initConf(instance='main'):
    conf=None
    try:
        if instance!='main':
            conf = hltdConf('/etc/hltd-'+instance+'.conf')
    except:pass
    if conf==None and instance=='main': conf = hltdConf('/etc/hltd.conf')
    return conf
