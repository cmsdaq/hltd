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
  if (( i!=4 && i!=5 && i!=6 )); then
    params="$params ${lines[i]}"
  fi
done

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
Version: 2.2.0
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

echo "#!/bin/bash" > %{buildroot}/opt/fff/configurefff.sh
echo
echo "if [ -n \"\\\$1\" ]; then"                                     >> %{buildroot}/opt/fff/configurefff.sh
echo "  if [ \\\$1 == \"hltd\" ]; then"                              >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/hltd/python/fillresources.py"                 >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/fff/setupmachine.py configure $params"        >> %{buildroot}/opt/fff/configurefff.sh
echo "  elif [ \\\$1 == \"init\" ]; then"                            >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/hltd/python/fillresources.py ignorecloud"     >> %{buildroot}/opt/fff/configurefff.sh
echo "    python2 /opt/fff/setupmachine.py configure $params"        >> %{buildroot}/opt/fff/configurefff.sh 
echo "  fi"                                                          >> %{buildroot}/opt/fff/configurefff.sh
echo "else"                                                          >> %{buildroot}/opt/fff/configurefff.sh
echo "  python2 /opt/hltd/python/fillresources.py"                   >> %{buildroot}/opt/fff/configurefff.sh
echo "  python2 /opt/fff/setupmachine.py configure $params"          >> %{buildroot}/opt/fff/configurefff.sh
echo "fi"                                                            >> %{buildroot}/opt/fff/configurefff.sh

echo " { \"login\":\"${dblogin}\" , \"password\":\"${dbpwd}\" , \"sid\":\"${dbsid}\" }"    >> %{buildroot}/opt/fff/db.jsn

%files
%defattr(-, root, root, -)
#/opt/fff
%attr( 755 ,root, root) /opt/fff/setupmachine.py
%attr( 755 ,root, root) /opt/fff/setupmachine.pyc
%attr( 755 ,root, root) /opt/fff/setupmachine.pyo
%attr( 755 ,root, root) /opt/fff/instances.input
%attr( 755 ,root, root) /opt/fff/configurefff.sh
%attr( 755 ,root, root) /opt/fff/dbcheck.py
%attr( 755 ,root, root) /opt/fff/dbcheck.pyc
%attr( 755 ,root, root) /opt/fff/dbcheck.pyo
%attr( 700 ,root, root) /opt/fff/db.jsn
%attr( 755 ,root, root) /opt/fff/init.d/fff
%attr( 644 ,root, root) /usr/lib/systemd/system/fff.service

%post
#echo "post install trigger"

%triggerin -- hltd
#echo "triggered on hltd update or install"

#disable sysv style service
/etc/init.d/soap2file stop || true
/sbin/chkconfig --del soap2file || true

rm -rf /etc/hltd.instances

#hltd configuration
/opt/fff/init.d/fff configure
role=\`/opt/fff/setupmachine.py getrole\`

#adjust ownership of unpriviledged child process log files
if [ -f /var/log/hltd/elastic.log ]; then
chown ${lines[9]} /var/log/hltd/elastic.log
fi

if [ -f /var/log/hltd/anelastic.log ]; then
chown ${lines[9]} /var/log/hltd/anelastic.log
fi

#update resource count for hltd (i.e. triggered at next service restart)
touch /opt/hltd/scratch/new-version || true

#notify systemd of updated unit files and enable them (but don't restart)
#unregister old sysV style scripts
/sbin/chkconfig --del hltd
/sbin/chkconfig --del fffmeta
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl reenable hltd
/usr/bin/systemctl reenable fff

#restart soapfile (process will not run if disabled in configuration, but service will be active)
/usr/bin/systemctl reenable soap2file
/usr/bin/systemctl start soap2file

%preun

if [ \$1 == 0 ]; then 

  #stop services if running (sysv and systemd)
  /etc/init.d/hltd stop || true
  /etc/init.d/soap2file stop || true
  /usr/bin/systemctl stop hltd
  /usr/bin/systemctl stop soap2file

  #unregister old sysV style scripts
  /sbin/chkconfig --del hltd || true
  /sbin/chkconfig --del fffmeta || true
  /sbin/chkconfig --del soap2file || true
  /usr/bin/systemctl disable hltd
  /usr/bin/systemctl disable fff
  /usr/bin/systemctl disable soap2file


fi

#%verifyscript

EOF

rpmbuild --target noarch --define "_topdir `pwd`/RPMBUILD" -bb fffmeta.spec

