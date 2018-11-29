#!/bin/bash -e
alias python=`readlink /usr/bin/python2`
python_dir=`readlink /usr/bin/python2`
# set the RPM build architecture
#BUILD_ARCH=$(uname -i)      # "i386" for SLC4, "x86_64" for SLC5
BUILD_ARCH=x86_64
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $SCRIPTDIR/..
BASEDIR=$PWD

# create a build area
echo "removing old build area"
rm -rf /tmp/hltd-build-tmp-area
echo "creating new build area"
mkdir  /tmp/hltd-build-tmp-area
cd     /tmp/hltd-build-tmp-area
TOPDIR=$PWD
echo "working in $PWD"

# we are done here, write the specs and make the fu***** rpm
cat > hltd.spec <<EOF
Name: hltd
Version: 2.3.2
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
mkdir -p etc/init.d

echo "Creating DQM directories"
mkdir -p etc/appliance/dqm_resources/idle
mkdir -p etc/appliance/dqm_resources/online
mkdir -p etc/appliance/dqm_resources/except
mkdir -p etc/appliance/dqm_resources/quarantined
mkdir -p etc/appliance/dqm_resources/cloud

echo "Copying files to their destination"
cp -R $BASEDIR/init.d/hltd.service  usr/lib/systemd/system/hltd.service
cp -R $BASEDIR/init.d/soap2file.service  usr/lib/systemd/system/soap2file.service
cp -R $BASEDIR/*                    opt/hltd
cp -R $BASEDIR/etc/hltd.conf        etc/
cp -R $BASEDIR/etc/hltd.conf        etc/hltd.conf.template
cp -R $BASEDIR/etc/logrotate.d/hltd etc/logrotate.d/
touch opt/hltd/scratch/new-version

echo "Deleting unnecessary files"
rm -rf opt/hltd/python/{*.pyc,*.pyo}
rm -rf opt/hltd/{bin,rpm,lib}
#rm -rf opt/hltd/rpm
#rm -rf opt/hltd/lib
rm -rf opt/hltd/scripts/paramcache*
rm -rf opt/hltd/scripts/*rpm.sh
rm -rf opt/hltd/scripts/postinstall.sh
rm -rf opt/hltd/scripts/*.php
rm -rf opt/hltd/init.d/*.service
rm -rf opt/hltd/init.d/fff*
rm -rf opt/hltd/python/setupmachine.py
rm -rf opt/hltd/python/dbcheck.py
rm -rf opt/hltd/TODO
rm -rf opt/hltd/test/*.gz

%post

%files
%dir %attr(777, -, -) /var/log/hltd
%dir %attr(777, -, -) /var/log/hltd/pid
%defattr(-, root, root, -)
/opt/hltd/
/etc/hltd.conf
/etc/hltd.conf.template
/etc/logrotate.d/hltd
/usr/lib/systemd/system/hltd.service
/usr/lib/systemd/system/soap2file.service
/etc/appliance

%preun
if [ \$1 == 0 ]; then
  /usr/bin/systemctl stop hltd || true
  /usr/bin/systemctl disable hltd || true
  /usr/bin/systemctl stop soap2file || true
  /usr/bin/systemctl disable soap2file || true
fi
EOF
mkdir -p RPMBUILD/{RPMS/{noarch},SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" -bb hltd.spec
#rm -rf patch-cmssw-tmp

