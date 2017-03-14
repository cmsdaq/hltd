#!/bin/bash -e
alias python=`readlink /usr/bin/python2`
python_dir=`readlink /usr/bin/python2`
# set the RPM build architecture
#BUILD_ARCH=$(uname -i)      # "i386" for SLC4, "x86_64" for SLC5
BUILD_ARCH=x86_64
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPTDIR/..

#run other script...
#$SCRIPTDIR/libshltdrpm.sh

BASEDIR=$PWD

# create a build area
echo "removing old build area"
rm -rf /tmp/hltd-build-tmp-area
echo "creating new build area"
mkdir  /tmp/hltd-build-tmp-area
cd     /tmp/hltd-build-tmp-area
TOPDIR=$PWD

echo "Moving files to their destination"
mkdir -p var/log/hltd
mkdir -p var/log/hltd/pid
mkdir -p opt/hltd
mkdir -p etc/logrotate.d
mkdir -p etc/appliance/resources/idle
mkdir -p etc/appliance/resources/online
mkdir -p etc/appliance/resources/except
mkdir -p etc/appliance/resources/quarantined
mkdir -p etc/appliance/resources/cloud
mkdir -p usr/lib/systemd/system
ls
cp -R $BASEDIR/scripts/hltd.service $TOPDIR/usr/lib/systemd/system/hltd.service
cp -R $BASEDIR/python/soap2file $TOPDIR/etc/init.d/soap2file
cp -R $BASEDIR/* $TOPDIR/opt/hltd
touch $TOPDIR/opt/hltd/scratch/new-version
cp -R $BASEDIR/etc/hltd.conf $TOPDIR/etc/
cp -R $BASEDIR/etc/hltd.conf $TOPDIR/etc/hltd.conf.template
cp -R $BASEDIR/etc/logrotate.d/hltd $TOPDIR/etc/logrotate.d/
echo "working in $PWD"
ls opt/hltd

echo "Creating DQM directories"
mkdir -p etc/appliance/dqm_resources/idle
mkdir -p etc/appliance/dqm_resources/online
mkdir -p etc/appliance/dqm_resources/except
mkdir -p etc/appliance/dqm_resources/quarantined
mkdir -p etc/appliance/dqm_resources/cloud

rm -rf $TOPDIR/opt/hltd/bin
rm -rf $TOPDIR/opt/hltd/rpm
rm -rf $TOPDIR/opt/hltd/lib
rm -rf $TOPDIR/opt/hltd/scripts/paramcache*
rm -rf $TOPDIR/opt/hltd/scripts/*rpm.sh
rm -rf $TOPDIR/opt/hltd/scripts/*.php
rm -rf $TOPDIR/opt/hltd/scripts/*.service
rm -rf $TOPDIR/opt/hltd/init.d/fff*
rm -rf $TOPDIR/opt/hltd/python/soap2file
rm -rf $TOPDIR/opt/hltd/python/setupmachine.py
rm -rf $TOPDIR/opt/hltd/python/dbcheck.py
rm -rf $TOPDIR/opt/hltd/TODO

cd $TOPDIR
# we are done here, write the specs and make the fu***** rpm
cat > hltd.spec <<EOF
Name: hltd
Version: 2.1.3
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
Provides:/usr/lib/systemd/system/fffmeta.service
Provides:/usr/lib/systemd/system/hltd.service
Provides:/etc/init.d/soap2file
Requires:hltd-libs >= 2.1.0,SOAPpy,python-simplejson >= 3.3.1,jsonMerger,python-psutil,python-dateutil,cx_Oracle

%description
fff hlt daemon

%prep
%build

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
%__install -d "%{buildroot}/var/log/hltd"
%__install -d "%{buildroot}/var/log/hltd/pid"
tar -C $TOPDIR -c opt/hltd | tar -xC \$RPM_BUILD_ROOT
tar -C $TOPDIR -c etc | tar -xC \$RPM_BUILD_ROOT
rm \$RPM_BUILD_ROOT/opt/hltd/TODO || true
%post
%files
%dir %attr(777, -, -) /var/log/hltd
%dir %attr(777, -, -) /var/log/hltd/pid
%defattr(-, root, root, -)
/opt/hltd/
/etc/hltd.conf
/etc/hltd.conf.template
/etc/logrotate.d/hltd
/usr/lib/systemd/system/fffmeta.service
/usr/lib/systemd/system/hltd.service
/etc/init.d/soap2file
/etc/appliance
%preun
if [ \$1 == 0 ]; then
  systemctl stop hltd || true
  systemctl disable hltd || true
  /sbin/service soap2file stop || true
fi
EOF
mkdir -p RPMBUILD/{RPMS/{noarch},SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" -bb hltd.spec
#rm -rf patch-cmssw-tmp

