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

echo "ES central server host or alias (without .cms/.cern.ch) (press enter for \"${lines[2]}\"):"
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

echo "CMSSW base (press enter for \"${lines[8]}\"):"
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


params=""
for (( i=0; i < ${NLINES}; i++ ))
do
  params="$params ${lines[i]}"
done
dbsid=${lines[4]}
dblogin=${lines[5]}
dbpwd=${lines[6]}

revsuffix=""
if [ ${lines[1]} != "null" ];
then
    revsuffix=${lines[1]}
fi

#write cache
if [ -f $SCRIPTDIR/$PARAMCACHE ];
then
    rm -rf -f $SCRIPTDIR/$PARAMCACHE
fi
for (( i=0; i < 12; i++ ))
do
  echo ${lines[$i]} >> $SCRIPTDIR/$PARAMCACHE
done

chmod 500 $SCRIPTDIR/$PARAMCACHE
# create a build area

if [ ${lines[0]} == "prod" ]; then
  PACKAGENAME="fffmeta"
elif [ ${lines[0]} == "vm" ]; then
  PACKAGENAME="fffmeta-vm"
else
  echo "Environment ${lines[0]} not supported. Available: prod or vm"
  exit 1
fi

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
Version: 2.1.1
Release: 0${revsuffix}
Summary: hlt daemon
License: gpl
Group: DAQ
Packager: smorovic
Source: none
%define _topdir $TOPDIR
BuildArch: $BUILD_ARCH
AutoReqProv: no
Requires: hltd >= 2.1.0, cx_Oracle

Provides:/opt/fff/configurefff.sh
Provides:/opt/fff/dbcheck.sh
Provides:/opt/fff/setupmachine.py
Provides:/opt/fff/disablenode.py
Provides:/opt/fff/dbcheck.py
Provides:/opt/fff/db.jsn
Provides:/opt/fff/instances.input
Provides:/etc/init.d/fffmeta
Provides:/etc/init.d/fff

#Provides:/opt/fff/backup/hltd.conf

%description
fffmeta configuration setup package

%prep
%build

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
%__install -d "%{buildroot}/opt/fff"
%__install -d "%{buildroot}/opt/fff/backup"
%__install -d "%{buildroot}/etc/init.d"

mkdir -p opt/fff/backup
mkdir -p etc/init.d/
cp $BASEDIR/python/setupmachine.py %{buildroot}/opt/fff/setupmachine.py
cp $BASEDIR/python/disablenode.py %{buildroot}/opt/fff/disablenode.py
cp $BASEDIR/python/dbcheck.py %{buildroot}/opt/fff/dbcheck.py
cp $BASEDIR/etc/instances.input %{buildroot}/opt/fff/instances.input
echo "#!/bin/bash" > %{buildroot}/opt/fff/configurefff.sh
echo

echo "if [ -n \"\\\$1\" ]; then"                                       >> %{buildroot}/opt/fff/configurefff.sh
echo "  if [ \\\$1 == \"hltd\" ]; then"                                >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/hltd/python/fillresources.py"                 >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/fff/setupmachine.py configure $params"        >> %{buildroot}/opt/fff/configurefff.sh
echo "  elif [ \\\$1 == \"init\" ]; then"                              >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/hltd/python/fillresources.py ignorecloud"     >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/fff/setupmachine.py configure $params"        >> %{buildroot}/opt/fff/configurefff.sh 
echo "  fi"                                                            >> %{buildroot}/opt/fff/configurefff.sh
echo "else"                                                            >> %{buildroot}/opt/fff/configurefff.sh
echo "  python2 /opt/hltd/python/fillresources.py"                   >> %{buildroot}/opt/fff/configurefff.sh
echo "  python2 /opt/fff/setupmachine.py configure $params"          >> %{buildroot}/opt/fff/configurefff.sh

echo "#!/bin/bash" > %{buildroot}/opt/fff/dbcheck.sh
echo "if [ -n \"\\\$1\" ]; then "                                   >> %{buildroot}/opt/fff/dbcheck.sh
echo "  python2 /opt/fff/dbcheck.py $dblogin $dbpwd $dbsid $1"    >> %{buildroot}/opt/fff/dbcheck.sh
echo "else" >> %{buildroot}/opt/fff/dbcheck.sh                      >> %{buildroot}/opt/fff/dbcheck.sh
echo "  python2 /opt/fff/dbcheck.py $dblogin $dbpwd $dbsid"       >> %{buildroot}/opt/fff/dbcheck.sh
echo "fi"                                                           >> %{buildroot}/opt/fff/dbcheck.sh

echo " { \"login\":\"${dblogin}\" , \"password\":\"${dbpwd}\" , \"sid\":\"${dbsid}\" }"    >> %{buildroot}/opt/fff/db.jsn

cp $BASEDIR/scripts/fff %{buildroot}/etc/init.d/fff

echo "#!/bin/bash"                       >> %{buildroot}/etc/init.d/fffmeta
echo "#"                                 >> %{buildroot}/etc/init.d/fffmeta
echo "# chkconfig:   2345 79 22"         >> %{buildroot}/etc/init.d/fffmeta
echo "#"                                 >> %{buildroot}/etc/init.d/fffmeta
echo "if [ \\\$1 == \"start\" ]; then"   >> %{buildroot}/etc/init.d/fffmeta
echo "  /opt/fff/configurefff.sh init"   >> %{buildroot}/etc/init.d/fffmeta
echo "  exit 0"                          >> %{buildroot}/etc/init.d/fffmeta
echo "fi"                                >> %{buildroot}/etc/init.d/fffmeta
echo "if [ \\\$1 == \"restart\" ]; then" >> %{buildroot}/etc/init.d/fffmeta
echo "/opt/fff/configurefff.sh init"     >> %{buildroot}/etc/init.d/fffmeta
echo "  exit 0"                          >> %{buildroot}/etc/init.d/fffmeta
echo "fi"                                >> %{buildroot}/etc/init.d/fffmeta
echo "if [ \\\$1 == \"status\" ]; then"  >> %{buildroot}/etc/init.d/fffmeta
echo "echo fffmeta does not have status" >> %{buildroot}/etc/init.d/fffmeta
echo "  exit 0"                          >> %{buildroot}/etc/init.d/fffmeta
echo "fi"                                >> %{buildroot}/etc/init.d/fffmeta


%files
%defattr(-, root, root, -)
#/opt/fff
%attr( 755 ,root, root) /opt/fff/setupmachine.py
%attr( 755 ,root, root) /opt/fff/setupmachine.pyc
%attr( 755 ,root, root) /opt/fff/setupmachine.pyo
%attr( 755 ,root, root) /opt/fff/disablenode.py
%attr( 755 ,root, root) /opt/fff/disablenode.pyc
%attr( 755 ,root, root) /opt/fff/disablenode.pyo
%attr( 755 ,root, root) /opt/fff/instances.input
%attr( 700 ,root, root) /opt/fff/configurefff.sh
%attr( 700 ,root, root) /opt/fff/dbcheck.sh
%attr( 755 ,root, root) /opt/fff/dbcheck.py
%attr( 755 ,root, root) /opt/fff/dbcheck.pyc
%attr( 755 ,root, root) /opt/fff/dbcheck.pyo
%attr( 700 ,root, root) /opt/fff/db.jsn
%attr( 755 ,root, root) /etc/init.d/fffmeta
%attr( 755 ,root, root) /etc/init.d/fff

%post
#echo "post install trigger"
chkconfig --del fffmeta
chkconfig --add fffmeta
#disabled, can be run manually for now

%triggerin -- hltd
#echo "triggered on hltd update or install"

#/sbin/service hltd stop || true
/sbin/service soap2file stop || true
rm -rf /etc/hltd.instances

python2 /opt/fff/setupmachine.py restore
python2 /opt/fff/setupmachine.py configure $params

#adjust ownership of unpriviledged child process log files

if [ -f /var/log/hltd/elastic.log ]; then
chown ${lines[9]} /var/log/hltd/elastic.log
fi

if [ -f /var/log/hltd/anelastic.log ]; then
chown ${lines[9]} /var/log/hltd/anelastic.log
fi

#set up resources for hltd (triggered at next service restart)
touch /opt/hltd/scratch/new-version || true
#/opt/hltd/python/fillresources.py

#/sbin/service hltd restart || true
/sbin/service soap2file restart || true

chkconfig --del hltd
chkconfig --del soap2file

chkconfig --add hltd
chkconfig --add soap2file

%preun

if [ \$1 == 0 ]; then 

  chkconfig --del fffmeta
  chkconfig --del elasticsearch
  chkconfig --del hltd
  chkconfig --del soap2file

  /sbin/service hltd stop || true

  python2 /opt/fff/setupmachine.py restore

fi

#TODO:
#%verifyscript

EOF

rpmbuild --target noarch --define "_topdir `pwd`/RPMBUILD" -bb fffmeta.spec

