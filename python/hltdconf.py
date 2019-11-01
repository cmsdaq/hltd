try:
  from ConfigParser import SafeConfigParser
except:
  from configparser import SafeConfigParser

import logging
import os
import datetime

class hltdConf:
    def __init__(self, conffile):
        cfg = SafeConfigParser()
        cfg.read(conffile)

        self.role = None
        self.elastic_bu_test = None
        self.elastic_runindex_url = None
        self.elastic_runindex_name = 'cdaq'
        self.fff_base = '/fff'
        self.fff_base_autofs = '/fff/BUs'
        self.watch_directory = None
        self.ramdisk_subdirectory = 'ramdisk' #local mountpoint
        self.output_subdirectory = 'output' #local mountpoint
        self.ramdisk_subdirectory_remote = 'ramdisk' #remote or on BU
        self.output_subdirectory_remote = 'ramdisk/output' #remore or on BU
        self.fastmon_insert_modulo = 1
        self.elastic_cluster = None
        self.log_dir = "/var/log/hltd"
        self.es_local = ""
        self.cloud_igniter_path = None

        for sec in cfg.sections():
            for item,value in cfg.items(sec):
                self.__dict__[item] = value

        #override default values into imposed types
        self.enabled = cfg.getboolean('General','enabled')
        self.mount_control_path = cfg.getboolean('General','mount_control_path')
        try:
          self.dynamic_mounts = cfg.getboolean('General','dynamic_mounts')
        except:
          self.dynamic_mounts = False
        try:
          self.static_blacklist = cfg.getboolean('General','static_blacklist')
        except:
          self.static_blacklist = False
        try:
          self.static_whitelist = cfg.getboolean('General','static_whitelist')
        except:
          self.static_whitelist = False

        #default
        try:
            self.run_number_padding = cfg.getint('General','run_number_padding')
        except:
            self.run_number_padding = 6

        self.delete_run_dir = cfg.getboolean('General','delete_run_dir')
        self.output_adler32 = cfg.getboolean('General','output_adler32')
        self.drop_at_fu = cfg.getboolean('General','drop_at_fu')

        self.use_elasticsearch = cfg.getboolean('Monitoring','use_elasticsearch')
        self.force_replicas = cfg.getint('Monitoring','force_replicas')
        self.force_shards = cfg.getint('Monitoring','force_shards')
        self.update_es_template = cfg.getboolean('Monitoring','update_es_template')
        try:
          self.mon_bu_cpus = cfg.getboolean('Monitoring','mon_bu_cpus')
        except:
          self.mon_bu_cpus = False

        self.cgi_port = cfg.getint('Web','cgi_port')
        self.cgi_instance_port_offset = cfg.getint('Web','cgi_instance_port_offset')
        self.soap2file_port = cfg.getint('Web','soap2file_port')

        #try:
        #    self.instance_same_destination=bool(self.instance_same_destination=="True")
        #except:
        #    self.instance_same_destination = True

        self.dqm_machine = cfg.getboolean('DQM','dqm_machine')
        if self.dqm_machine:
            self.resource_base = self.dqm_resource_base
        self.dqm_globallock = cfg.getboolean('DQM','dqm_globallock')

        self.process_restart_delay_sec = cfg.getfloat('Recovery','process_restart_delay_sec')
        self.process_restart_limit = cfg.getint('Recovery','process_restart_limit')
        self.cmssw_threads_autosplit = cfg.getint('CMSSW','cmssw_threads_autosplit')
        self.cmssw_threads = cfg.getint('CMSSW','cmssw_threads')
        self.cmssw_streams = cfg.getint('CMSSW','cmssw_streams')
        self.resource_use_fraction = cfg.getfloat('Resources','resource_use_fraction')
        self.auto_clear_quarantined = cfg.getboolean('Recovery','auto_clear_quarantined')
        self.max_local_disk_usage = cfg.getint('Resources','max_local_disk_usage')
        self.dynamic_resources = cfg.getboolean('Resources','dynamic_resources')
        self.service_log_level = getattr(logging,self.service_log_level)
        self.autodetect_parameters()

        self.elastic_cluster=self.elastic_runindex_name

    def dump(self):
        logging.info( '<hltd STATUS time="' + str(datetime.datetime.now()).split('.')[0] + '" user:' + self.user + ' role:' + self.role + '>')

    def autodetect_parameters(self):
        #NOTE: will not work with daq3val if role is not set
        if not self.role and (os.uname()[1].startswith('bu-') or os.uname()[1].startswith('dvbu-')) or os.uname()[1].startswith('d3vrubu-'):
            self.role = 'bu'
        elif not self.role:
            self.role = 'fu'
        if not self.watch_directory:
            if self.role == 'bu': self.watch_directory='/fff/ramdisk'
            if self.role == 'fu': self.watch_directory='/fff/data'

def initConf(instance='main'):
    conf=None
    try:
        if instance!='main':
            conf = hltdConf('/etc/hltd-'+instance+'.conf')
    except:pass
    if conf==None and instance=='main': conf = hltdConf('/etc/hltd.conf')
    return conf
