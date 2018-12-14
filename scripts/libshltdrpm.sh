#!/bin/bash -e

alias python=`readlink /usr/bin/python2`
python_dir=`readlink /usr/bin/python2`
python_version=${python_dir:6}

# set the RPM build architecture
#BUILD_ARCH=$(uname -i)      # "i386" for SLC4, "x86_64" for SLC5
BUILD_ARCH=x86_64
SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPTDIR/..
BASEDIR=$PWD

# create a build area

echo "removing old build area"
rm -rf /tmp/hltd-libs-build-tmp-area
echo "creating new build area"
mkdir  /tmp/hltd-libs-build-tmp-area
cd     /tmp/hltd-libs-build-tmp-area
TOPDIR=$PWD

mkdir -p $TOPDIR/opt/hltd
cp -r $BASEDIR/lib $TOPDIR/opt/hltd

echo "Moving files to their destination"
mkdir -p usr/lib64/$python_dir/site-packages
#mkdir -p usr/lib64/$python_dir/site-packages/pyelasticsearch
mkdir -p usr/lib64/$python_dir/site-packages/elasticsearch5
mkdir -p usr/lib64/$python_dir/site-packages/urllib3_hltd

cd $TOPDIR
#urllib3 1.10 (renamed urllib3_hltd)
#cd opt/hltd/lib/urllib3-1.10/
#urllib3 1.24.1 (renamed urllib3_hltd)
cd opt/hltd/lib/urllib3-1.24.1/
python ./setup.py -q build
python - <<'EOF'
import compileall
compileall.compile_dir("build/lib/urllib3_hltd",quiet=True)
EOF
python -O - <<'EOF'
import compileall
compileall.compile_dir("build/lib/urllib3_hltd",quiet=True)
EOF
cp -R build/lib/urllib3_hltd/* $TOPDIR/usr/lib64/$python_dir/site-packages/urllib3_hltd/

#cd $TOPDIR
##pyelasticsearch
#cd opt/hltd/lib/pyelasticsearch-1.0/
#python ./setup.py -q build
#python - <<'EOF'
#import compileall
#compileall.compile_dir("build/lib/pyelasticsearch/",quiet=True)
#EOF
#python -O - <<'EOF'
#import compileall
#compileall.compile_dir("build/lib/pyelasticsearch/",quiet=True)
#EOF
#cp -R build/lib/pyelasticsearch/* $TOPDIR/usr/lib64/$python_dir/site-packages/pyelasticsearch/
#cp -R pyelasticsearch.egg-info/ $TOPDIR/usr/lib64/$python_dir/site-packages/pyelasticsearch/


cd $TOPDIR
#elasticsearch-py
cd opt/hltd/lib/elasticsearch-py-5.5.5/
python ./setup.py -q build
python - <<'EOF'
import compileall
compileall.compile_dir("build/lib/elasticsearch5",quiet=True)
EOF
python -O - <<'EOF'
import compileall
compileall.compile_dir("build/lib/elasticsearch5",quiet=True)
EOF
cp -R build/lib/elasticsearch5/* $TOPDIR/usr/lib64/$python_dir/site-packages/elasticsearch5/


cd $TOPDIR
#_zlibextras library
cd opt/hltd/lib/python-zlib-extras-0.1/
rm -rf build
python ./setup.py -q build
cp -R build/lib.linux-x86_64-${python_version}/_zlibextras.so $TOPDIR/usr/lib64/$python_dir/site-packages/


cd $TOPDIR
#python-prctl
cd opt/hltd/lib/python-prctl/
./setup.py -q build
#python - <<'EOF'
python - <<EOF
import py_compile
py_compile.compile("build/lib.linux-x86_64-${python_version}/prctl.py")
EOF
python -O - <<EOF
import py_compile
py_compile.compile("build/lib.linux-x86_64-${python_version}/prctl.py")
EOF
cp build/lib.linux-x86_64-${python_version}/prctl.pyo $TOPDIR/usr/lib64/$python_dir/site-packages
cp build/lib.linux-x86_64-${python_version}/prctl.py $TOPDIR/usr/lib64/$python_dir/site-packages
cp build/lib.linux-x86_64-${python_version}/prctl.pyc $TOPDIR/usr/lib64/$python_dir/site-packages
cp build/lib.linux-x86_64-${python_version}/_prctl.so $TOPDIR/usr/lib64/$python_dir/site-packages
cat > $TOPDIR/usr/lib64/$python_dir/site-packages/python_prctl-1.5.0-py$python_version.egg-info <<EOF
Metadata-Version: 1.0
Name: python-prctl
Version: 1.5.0
Summary: Python(ic) interface to the linux prctl syscall
Home-page: http://github.com/seveas/python-prctl
Author: Dennis Kaarsemaker
Author-email: dennis@kaarsemaker.net
License: UNKNOWN
Description: UNKNOWN
Platform: UNKNOWN
Classifier: Development Status :: 5 - Production/Stable
Classifier: Intended Audience :: Developers
Classifier: License :: OSI Approved :: GNU General Public License (GPL)
Classifier: Operating System :: POSIX :: Linux
Classifier: Programming Language :: C
Classifier: Programming Language :: Python
Classifier: Topic :: Security
EOF

cd $TOPDIR
cd opt/hltd/lib/python-inotify-0.5/
./setup.py -q build
cp build/lib.linux-x86_64-${python_version}/inotify/_inotify.so $TOPDIR/usr/lib64/$python_dir/site-packages
cp build/lib.linux-x86_64-${python_version}/inotify/watcher.py $TOPDIR/usr/lib64/$python_dir/site-packages
python - <<EOF
import py_compile
py_compile.compile("build/lib.linux-x86_64-${python_version}/inotify/watcher.py")
EOF
cp build/lib.linux-x86_64-${python_version}/inotify/watcher.pyc $TOPDIR/usr/lib64/$python_dir/site-packages/
cat > $TOPDIR/usr/lib64/$python_dir/site-packages/python_inotify-0.5.egg-info <<EOF
Metadata-Version: 1.0
Name: python-inotify
Version: 0.5
Summary: Interface to Linux inotify subsystem
Home-page: 'http://www.serpentine.com/
Author: Bryan O'Sullivan
Author-email: bos@serpentine.com
License: LGPL
Platform: Linux
Classifier: Development Status :: 5 - Production/Stable
Classifier: Environment :: Console
Classifier: Intended Audience :: Developers
Classifier: License :: OSI Approved :: LGPL
Classifier: Natural Language :: English
Classifier: Operating System :: POSIX :: Linux
Classifier: Programming Language :: Python
Classifier: Programming Language :: Python :: 2.4
Classifier: Programming Language :: Python :: 2.5
Classifier: Programming Language :: Python :: 2.6
Classifier: Programming Language :: Python :: 2.7
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Classifier: Topic :: System :: Filesystems
Classifier: Topic :: System :: Monitoring
EOF


cd $TOPDIR
cd opt/hltd/lib/python-procname/
./setup.py -q build
cp build/lib.linux-x86_64-${python_version}/procname.so $TOPDIR/usr/lib64/$python_dir/site-packages

cd $TOPDIR
rm -rf opt

# we are done here, write the specs and make the fu***** rpm
cat > hltd-libs.spec <<EOF
Name: hltd-libs
Version: 2.4.0
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
#Provides:/usr/lib64/$python_dir/site-packages/prctl.pyc
Requires:python,libcap,python-six >= 1.9,python-simplejson >= 3.3.1,python-requests

%description
fff hlt daemon libraries

%prep
%build

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT
tar -C $TOPDIR -c usr | tar -xC \$RPM_BUILD_ROOT
%post
%files
%defattr(-, root, root, -)
/usr/lib64/$python_dir/site-packages/*prctl*
/usr/lib64/$python_dir/site-packages/*watcher*
/usr/lib64/$python_dir/site-packages/*_inotify.so*
/usr/lib64/$python_dir/site-packages/*python_inotify*
/usr/lib64/$python_dir/site-packages/*_zlibextras.so
#/usr/lib64/$python_dir/site-packages/pyelasticsearch
/usr/lib64/$python_dir/site-packages/elasticsearch5
/usr/lib64/$python_dir/site-packages/urllib3_hltd
/usr/lib64/$python_dir/site-packages/procname.so
EOF
mkdir -p RPMBUILD/{RPMS/{noarch},SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" -bb hltd-libs.spec

