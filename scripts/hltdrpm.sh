#!/bin/bash -e
BUILD_ARCH=x86_64
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPTDIR/..
BASEDIR=$PWD

PARAMCACHE="paramcache"
NLINES=15
ASK="1"

if [ -n "$1" ]; then
  if [ "$1" = "--batch" ]; then
  ASK="0"
  fi

  if [ "$1" = "-b" ]; then
  ASK="0"
  fi

  if [ $ASK = "0" ]; then #check $2 if found
    if [ -n "$2" ]; then
            PARAMCACHE=${2##*/}
    fi
  fi
  if [ $ASK = "1" ]; then #take $1 
    PARAMCACHE=${1##*/}
  fi
fi

echo "Using cache file $PARAMCACHE"

if [ -f $SCRIPTDIR/$PARAMCACHE ];
then
  readarray lines < $SCRIPTDIR/$PARAMCACHE
  for (( i=0; i < ${NLINES}; i++ ))
  do
    lines[$i]=`echo -n ${lines[$i]} | tr -d "\n"`
  done
else
  for (( i=0; i < ${NLINES}; i++ ))
  do
    lines[$i]=""
  done
fi

if [ $ASK = "1" ]; then

echo "This is the hltd build script. It will now ask for several configuration parameters."
echo "Use -b cmdline parameter to build from cache without waiting for input"
echo "   ... press any key to continue ..."
read readin


echo "Python version - v3.6: python3.4 or python3.6 (press enter for \"${lines[0]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[0]=$readin
fi

echo "rpm revision suffix (enter null if none, press enter for \"${lines[1]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[1]=$readin
fi

echo "ES central server host or alias (with .cms or .cern.ch) (press enter for \"${lines[2]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[2]=$readin
fi

echo "ES local (previously tribe) server host or alias (without .cms/.cern.ch) (press enter for \"${lines[3]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[3]=$readin
fi

echo "HwCfg DB SID to be matched with tnsnames.ora (press enter for: \"${lines[4]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[4]=$readin
fi

echo "HwCfg DB username (press enter for: \"${lines[5]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[5]=$readin
fi

echo "HwCfg DB password (press enter for: \"${lines[6]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[6]=$readin
fi

echo "equipment set (press enter for: \"${lines[7]}\") - type 'latest' or enter a specific one:"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[7]=$readin
fi

echo "CMSSW dist base (press enter for \"${lines[8]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[8]=$readin
fi

echo "username for CMSSW jobs (press enter for: \"${lines[9]}\"):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[9]=$readin
fi

echo "number of threads per process (press enter for: ${lines[10]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[10]=$readin
fi

echo "number of framework streams per process (press enter for: ${lines[11]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[11]=$readin
fi

echo "CMSSW log collection level (DEBUG,INFO,WARNING,ERROR or FATAL - default is ERROR) (press enter for: ${lines[12]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[12]=$readin
fi

echo "hltd log collection level (DEBUG,INFO,WARNING,ERROR or FATAL - default is ERROR) (press enter for: ${lines[13]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[13]=$readin
fi

echo "password for elasticsearch user hltdwriter (press enter for: ${lines[14]}):"
readin=""
read readin
if [ ${#readin} != "0" ]; then
lines[14]=$readin
fi


fi #ask

#database rpm build parameters
dbsid=${lines[4]}
dblogin=${lines[5]}
dbpwd=${lines[6]}
elasticpwd=${lines[14]}

#special RPM revision suffix, if defined
revsuffix=""
if [ ${lines[1]} != "null" ];
then
    revsuffix=${lines[1]}
fi


pythonlink=${lines[0]}
while ! [ "$pythonlink" = "" ]
do
  pythonlinklast=$pythonlink
  readlink /usr/bin/$pythonlink > $SCRIPTDIR/pytmp | true
  pythonlink=`cat $SCRIPTDIR/pytmp`
  rm -rf $SCRIPTDIR/pytmp
  #echo "running readlink /usr/bin/$pythonlinklast --> /usr/bin/$pythonlink"
done
pythonlinklast=`basename $pythonlinklast`
echo "will use python version: $pythonlinklast"

#other parameters
#env=${lines[0]}
#pythonver=${lines[0]}
pythonver=$pythonlinklast
centrales=${lines[2]}
locales=${lines[3]}
eqset=${lines[7]}
cmsswbase=${lines[8]}
user=${lines[9]}
nthreads=${lines[10]}
nfwkstreams=${lines[11]}
cmsswloglevel=${lines[12]}
hltdloglevel=${lines[13]}

#write down parameters in db.jsn
cat > $SCRIPTDIR/temp_db.jsn <<EOF
{
  "env":"prod",
  "pythonver":"${pythonver}",
  "revsuffix":"${revsuffix}",
  "centrales":"${centrales}",
  "locales":"${locales}",
  "eqset":"${eqset}",
  "cmsswbase":"${cmsswbase}",
  "user":"${user}",
  "nthreads":"${nthreads}",
  "nfwkstreams":"${nfwkstreams}",
  "cmsswloglevel":"${cmsswloglevel}",
  "hltdloglevel":"${hltdloglevel}",
  "login":"${dblogin}",
  "password":"${dbpwd}",
  "sid":"${dbsid}",
  "elasticpwd":"${elasticpwd}"
}
EOF

#update cache file
if [ -f $SCRIPTDIR/$PARAMCACHE ];
then
    rm -rf -f $SCRIPTDIR/$PARAMCACHE
fi
for (( i=0; i < ${NLINES}; i++ ))
do
  echo ${lines[$i]} >> $SCRIPTDIR/$PARAMCACHE
done

#contains secrets
chmod 500 $SCRIPTDIR/$PARAMCACHE

#determine VM or PROD RPM build (TODO: autodetect in rpm script based on hostname prefix)
#if [ ${lines[0]} == "prod" ]; then
PACKAGENAME="hltd"
#elif [ ${lines[0]} == "vm" ]; then
#  PACKAGENAME="hltd-vm"
#else
#  echo "Environment ${lines[0]} not supported. Available: prod or vm"
#  exit 1
#fi


# set the RPM build architecture
#BUILD_ARCH=$(uname -i)      # "i386" for SLC4, "x86_64" for SLC5

cd $SCRIPTDIR/..
BASEDIR=$PWD

# create a build area
echo "removing old build area"
rm -rf /tmp/$PACKAGENAME-build-tmp
echo "creating new build area"
mkdir  /tmp/$PACKAGENAME-build-tmp
cd     /tmp/$PACKAGENAME-build-tmp
mkdir BUILD
mkdir RPMS
TOPDIR=$PWD
echo "working in $PWD"
#ls

pypkgprefix="python"
pkgsuffix=""
pkgobsoletes=""
soappy=",SOAPpy"
if [ $pythonver = "python3.6" ]; then
  pypkgprefix="python36"
  pkgsuffix="-python36"
  pkgobsoletes=", hltd"
  soappy=""
fi

if [ $pythonver = "python3.4" ]; then
  pypkgprefix="python34"
  pkgsuffix="-python34"
  pkgobsoletes=", hltd"
  soappy=""
fi



# we are done here, write the specs and make the fu***** rpm
cat > hltd.spec <<EOF
Name: $PACKAGENAME$pkgsuffix
Version: 2.7.3
Release: 0
Summary: hlt daemon
License: gpl
Group: DAQ
Packager: smorovic
Source: none
%define _tmppath $TOPDIR/hltd-build
BuildRoot: %{_tmppath}
BuildArch: $BUILD_ARCH
AutoReqProv: no
Provides:/opt/hltd
Provides:/etc/hltd.conf
Provides:/etc/hltd.conf.template
Provides:/etc/logrotate.d/hltd
Provides:/usr/lib/systemd/system/hltd.service
Provides:/usr/lib/systemd/system/soap2file.service

Provides:/opt/fff/configurefff.sh
Provides:/opt/fff/setupmachine.py
Provides:/opt/fff/dbcheck.py
Provides:/opt/fff/db.jsn
Provides:/opt/fff/instances.input
Provides:/opt/fff/init.d/fff
Provides:/opt/fff/init.d/hltd
Provides:/opt/fff/postinstall.sh
Provides:/usr/lib/systemd/system/fff.service

Requires:hltd-libs$pkgsuffix >= 2.4.0 $soappy,jsonMerger,${pypkgprefix}-psutil,${pypkgprefix}-dateutil
Obsoletes: fffmeta <= 2.4.0, fffmeta-vm <= 2.4.0 $pkgobsoletes

#force python bytecompile to use proper python version
%global __python %{__${pythonver}}

%description
fff hlt daemon

%prep

%build

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
%__install -d "%{buildroot}/var/cache/hltd"
%__install -d "%{buildroot}/var/log/hltd"
%__install -d "%{buildroot}/var/log/hltd/pid"
%__install -d "%{buildroot}/opt/fff"
%__install -d "%{buildroot}/opt/fff/init.d"

#tar -C $TOPDIR -c opt/hltd | tar -xC \$RPM_BUILD_ROOT
#tar -C $TOPDIR -c etc | tar -xC \$RPM_BUILD_ROOT
#tar -C $TOPDIR -c usr | tar -xC \$RPM_BUILD_ROOT

cd \$RPM_BUILD_ROOT
echo "Creating directories"
mkdir -p opt/hltd
mkdir -p etc/logrotate.d
mkdir -p etc/appliance/resources/idle
mkdir -p etc/appliance/resources/online
mkdir -p etc/appliance/resources/except
mkdir -p etc/appliance/resources/quarantined
mkdir -p etc/appliance/resources/cloud
mkdir -p usr/lib/systemd/system
#mkdir -p %{buildroot}/usr/lib/systemd/system 
mkdir -p etc/init.d
mkdir -p %{buildroot}/opt/fff/init.d

echo "Creating DQM directories"
mkdir -p etc/appliance/dqm_resources/idle
mkdir -p etc/appliance/dqm_resources/online
mkdir -p etc/appliance/dqm_resources/except
mkdir -p etc/appliance/dqm_resources/quarantined
mkdir -p etc/appliance/dqm_resources/cloud

echo "Copying files to their destination"
cp $BASEDIR/init.d/fff.service      usr/lib/systemd/system/fff.service
cp -R $BASEDIR/init.d/hltd.service  usr/lib/systemd/system/hltd.service
cp -R $BASEDIR/init.d/soap2file.service  usr/lib/systemd/system/soap2file.service
cp -R $BASEDIR/*                    opt/hltd
cp -R $BASEDIR/etc/hltd.conf        etc/
cp -R $BASEDIR/etc/hltd.conf        etc/hltd.conf.template
cp -R $BASEDIR/etc/logrotate.d/hltd etc/logrotate.d/
rm -rf opt/hltd/init.d

cp $BASEDIR/init.d/fff %{buildroot}/opt/fff/init.d/
cp $BASEDIR/init.d/hltd %{buildroot}/opt/fff/init.d/
cp $BASEDIR/python/setupmachine.py %{buildroot}/opt/fff/setupmachine.py
cp $BASEDIR/python/dbcheck.py %{buildroot}/opt/fff/dbcheck.py
cp $BASEDIR/etc/instances.input %{buildroot}/opt/fff/instances.input
cp $BASEDIR/scripts/postinstall.sh %{buildroot}/opt/fff/postinstall.sh
mv $BASEDIR/scripts/temp_db.jsn %{buildroot}/opt/fff/db.jsn
cp $BASEDIR/scripts/configurefff.sh %{buildroot}/opt/fff/configurefff.sh

echo "modifying python executable specification to ${pythonver}"
grep -rl "\#\!/bin/env python" %{buildroot}/opt/fff/*.py          | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'
grep -rl "\#\!/bin/env python" %{buildroot}/opt/fff/init.d/hltd   | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'
grep -rl "\#\!/bin/env python" %{buildroot}/opt/fff/init.d/fff  | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'
grep -rl "\#\!/bin/env python" %{buildroot}/opt/hltd/cgi/*.py     | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'
grep -rl "\#\!/bin/env python" %{buildroot}/opt/hltd/python/*.py  | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'
grep -rl "\#\!/bin/env python" %{buildroot}/opt/hltd/scripts/*.py | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'
grep -rl "\#\!/bin/env python" %{buildroot}/opt/hltd/test/*.py    | xargs sed -i 's/^#!\/bin\/env python/#!\/bin\/env ${pythonver}/g'

touch opt/hltd/scratch/new-version

echo "Deleting unnecessary files"
rm -rf opt/hltd/{bin,rpm,lib}
rm -rf opt/hltd/scripts/paramcache*
rm -rf opt/hltd/scripts/*rpm.sh
rm -rf opt/hltd/scripts/postinstall.sh
rm -rf opt/hltd/scripts/*.php
#rm -rf opt/fff/init.d/*.service
rm -rf opt/hltd/python/setupmachine.py
rm -rf opt/hltd/python/dbcheck.py
rm -rf opt/hltd/TODO
rm -rf opt/hltd/test/*.gz

%post
chown daqlocal /opt/fff/db.jsn #possibly not needed
/opt/fff/postinstall.sh

%files
%dir %attr(777, -, -) /var/cache/hltd
%dir %attr(777, -, -) /var/log/hltd
%dir %attr(777, -, -) /var/log/hltd/pid
%defattr(-, root, root, -)
/opt/hltd/
/etc/hltd.conf
/etc/hltd.conf.template
/etc/logrotate.d/hltd
%attr( 644 ,root, root) /usr/lib/systemd/system/hltd.service
%attr( 644 ,root, root) /usr/lib/systemd/system/soap2file.service
%attr( 644 ,root, root) /usr/lib/systemd/system/fff.service
/etc/appliance
%attr( 755 ,root, root) /opt/fff/setupmachine.py
%attr( 755 ,root, root) /opt/fff/instances.input
%attr( 755 ,root, root) /opt/fff/configurefff.sh
%attr( 755 ,root, root) /opt/fff/postinstall.sh
%attr( 755 ,root, root) /opt/fff/dbcheck.py
%attr( 400 ,daqlocal, daqlocal) /opt/fff/db.jsn
%attr( 755 ,root, root) /opt/fff/init.d/fff
%attr( 755 ,root, root) /opt/fff/init.d/hltd


%preun
if [ \$1 == 0 ]; then
  /usr/bin/systemctl stop hltd || true
  /usr/bin/systemctl disable hltd || true
  /usr/bin/systemctl stop soap2file || true
  /usr/bin/systemctl disable soap2file || true
  /usr/bin/systemctl disable fff

fi
EOF
mkdir -p RPMBUILD/{RPMS/{noarch},SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" -bb hltd.spec
#rm -rf patch-cmssw-tmp

