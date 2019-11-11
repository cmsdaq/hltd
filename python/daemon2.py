import sys, os, time
import subprocess
import re
import logging
#from aUtils import * #for stdout and stderr redirection
from configparser import SafeConfigParser


#Output redirection class (used to set up redirections)
class stdOutLog:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    def write(self, message):
        self.logger.debug(message)
    def flush(self):
        return
class stdErrorLog:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    def write(self, message):
        self.logger.error(message)
    def flush(self):
        return


def do_umount(mpoint):
        try:
            subprocess.check_call(['umount',mpoint])
        except subprocess.CalledProcessError as err1:
            if err1.returncode>1:
                try:
                    time.sleep(0.5)
                    subprocess.check_call(['umount','-f',mpoint])
                except subprocess.CalledProcessError as err2:
                    if err2.returncode>1:
                        try:
                            time.sleep(1)
                            subprocess.check_call(['umount','-f',mpoint])
                        except subprocess.CalledProcessError as err3:
                            if err3.returncode>1:
                                sys.stdout.write("Error calling umount (-f) in cleanup_mountpoints\n")
                                sys.stdout.write(str(err3.returncode)+"\n")
                                return False
        except Exception as ex:
            sys.stdout.write(ex.args[0]+"\n")
        return True

#NOTE: this is used by systemd hltd post-stop
def emergencyUmount(conffile):

        cfg = SafeConfigParser()
        cfg.read(conffile)

        local_mode=False
        bu_base_dir=None
        bu_base_dir_autofs=None
        ramdisk_subdirectory = 'ramdisk'
        output_subdirectory = 'output'
        role = None


        for sec in cfg.sections():
            for item,value in cfg.items(sec):
                if item=='local_mode':local_mode=(value=='True')
                if item=='ramdisk_subdirectory':ramdisk_subdirectory=value
                if item=='output_subdirectory' :output_subdirectory=value
                if item=='bu_base_dir':bu_base_dir=value
                if item=='bu_base_dir_autofs':bu_base_dir_autofs=value
                if item=='role':role=value

        if role!='fu' or local_mode: return
        process = subprocess.Popen(['mount'],stdout=subprocess.PIPE)
        out=process.communicate()[0]
        if not isinstance(out,str): out = out.decode("utf-8")
        mounts = re.findall(bu_base_dir+'[0-9]+',out) + re.findall(bu_base_dir+'-CI/',out) + re.findall(bu_base_dir_autofs+'/',out)
        mounts = sorted(list(set(mounts)))
        for mpoint in mounts:
            point = mpoint.rstrip('/')
            sys.stdout.write("trying emergency umount of "+point+"\n")
            if do_umount(os.path.join('/'+point,ramdisk_subdirectory))==False:return False
            if not point.rstrip('/').endswith("-CI"):
                if do_umount(os.path.join('/'+point,output_subdirectory))==False:return False

