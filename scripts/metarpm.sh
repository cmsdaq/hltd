#!/bin/bash -e
BUILD_ARCH=noarch
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPTDIR/..
BASEDIR=$PWD

PARAMCACHE="paramcache"
NLINES=14

if [ -n "$1" ]; then
  #PARAMCACHE=$1
  PARAMCACHE=${1##*/}
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

echo "Environment (prod,vm) (press enter for \"${lines[0]}\"):"
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

#database rpm build parameters
dbsid=${lines[4]}
dblogin=${lines[5]}
dbpwd=${lines[6]}

#special RPM revision suffix, if defined
revsuffix=""
if [ ${lines[1]} != "null" ];
then
    revsuffix=${lines[1]}
fi

#other parameters
env=${lines[0]}
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
  "env":"${env}",
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
  "sid":"${dbsid}"
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

#determine VM or PROD RPM build
if [ ${lines[0]} == "prod" ]; then
  PACKAGENAME="fffmeta"
elif [ ${lines[0]} == "vm" ]; then
  PACKAGENAME="fffmeta-vm"
else
  echo "Environment ${lines[0]} not supported. Available: prod or vm"
  exit 1
fi

# create a build area
echo "removing old build area"
rm -rf /tmp/$PACKAGENAME-build-tmp
echo "creating new build area"
mkdir  /tmp/$PACKAGENAME-build-tmp
ls
cd     /tmp/$PACKAGENAME-build-tmp
mkdir BUILD
mkdir RPMS
TOPDIR=$PWD
echo "working in $PWD"
ls

cd $TOPDIR
# we are done here, write the specs and make the fu***** rpm
cat > fffmeta.spec <<EOF
Name: $PACKAGENAME
Version: 2.2.3
Release: 0${revsuffix}
Summary: hlt daemon
License: gpl
Group: DAQ
Packager: smorovic
Source: none
%define _topdir $TOPDIR
BuildArch: $BUILD_ARCH
AutoReqProv: no
Requires: hltd >= 2.1.0

Provides:/opt/fff/configurefff.sh
Provides:/opt/fff/setupmachine.py
Provides:/opt/fff/dbcheck.py
Provides:/opt/fff/db.jsn
Provides:/opt/fff/instances.input
Provides:/opt/fff/init.d/fff
Provides:/opt/fff/postinstall.sh
Provides:/usr/lib/systemd/system/fff.service

%description
fffmeta configuration setup package

%prep
%build

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
%__install -d "%{buildroot}/opt/fff"
%__install -d "%{buildroot}/etc/init.d"

mkdir -p %{buildroot}/opt/fff/init.d
mkdir -p %{buildroot}/usr/lib/systemd/system
cp $BASEDIR/init.d/fff %{buildroot}/opt/fff/init.d/fff
cp $BASEDIR/init.d/fff.service %{buildroot}/usr/lib/systemd/system/fff.service
cp $BASEDIR/python/setupmachine.py %{buildroot}/opt/fff/setupmachine.py
cp $BASEDIR/python/dbcheck.py %{buildroot}/opt/fff/dbcheck.py
cp $BASEDIR/etc/instances.input %{buildroot}/opt/fff/instances.input
cp $BASEDIR/scripts/postinstall.sh %{buildroot}/opt/fff/postinstall.sh
cp $BASEDIR/scripts/temp_db.jsn %{buildroot}/opt/fff/db.jsn
cp $BASEDIR/scripts/configurefff.sh %{buildroot}/opt/fff/configurefff.sh

%files
%defattr(-, root, root, -)
#/opt/fff
%attr( 755 ,root, root) /opt/fff/setupmachine.py
%attr( 755 ,root, root) /opt/fff/setupmachine.pyc
%attr( 755 ,root, root) /opt/fff/setupmachine.pyo
%attr( 755 ,root, root) /opt/fff/instances.input
%attr( 755 ,root, root) /opt/fff/configurefff.sh
%attr( 755 ,root, root) /opt/fff/postinstall.sh
%attr( 755 ,root, root) /opt/fff/dbcheck.py
%attr( 755 ,root, root) /opt/fff/dbcheck.pyc
%attr( 755 ,root, root) /opt/fff/dbcheck.pyo
%attr( 700 ,root, root) /opt/fff/db.jsn
%attr( 755 ,root, root) /opt/fff/init.d/fff
%attr( 644 ,root, root) /usr/lib/systemd/system/fff.service

%post
#echo "post install trigger"

%triggerin -- hltd
#echo "triggered on hltd update or install. Running fffmeta postinstall script..."
/opt/fff/postinstall.sh

%preun

if [ \$1 == 0 ]; then 

  #stop services if running (sysv and systemd)
  /etc/init.d/hltd stop || true
  /opt/hltd/python/soap2file.py stop || true
  /usr/bin/systemctl stop hltd
  /usr/bin/systemctl stop soap2file

  #unregister old sysV style scripts
  /sbin/chkconfig --del hltd >& /dev/null || true
  /sbin/chkconfig --del fffmeta >& /dev/null || true
  /sbin/chkconfig --del soap2file >& /dev/null || true
  /usr/bin/systemctl disable hltd
  /usr/bin/systemctl disable fff
  /usr/bin/systemctl disable soap2file

fi

#%verifyscript

EOF

rpmbuild --target noarch --define "_topdir `pwd`/RPMBUILD" -bb fffmeta.spec
