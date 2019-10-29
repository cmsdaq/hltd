#!/bin/bash -e

# set the RPM build architecture
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

if ! [ -z $1 ]; then
  rl=$1
  if ! [ -f /usr/bin/$rl ]; then
    echo "not found: $1"
    exit 1
  fi
else
  #take what is used for hltd
  PARAMCACHE="paramcache"
  rl="python3.4"
  if [ -f $SCRIPTDIR/$PARAMCACHE ];
  then
    readarray lines < $SCRIPTDIR/$PARAMCACHE
    #first line:
    rl=`echo -n ${lines[$i]} | tr -d "\n"`
  fi
fi 

pythonlink=$rl

while ! [ "$pythonlink" = "" ]
do
  pythonlinklast=$pythonlink
  readlink /usr/bin/$pythonlink > pytmp | true
  pythonlink=`cat pytmp`
  rm -rf pytmp
  #echo "running readlink /usr/bin/$pythonlinklast --> /usr/bin/$pythonlink"
done
pythonlinklast=`basename $pythonlinklast`
echo "will compile packages for: $pythonlinklast"
pyexec=$pythonlinklast
python_dir=$pythonlinklast
python_version=${python_dir:6}

mkdir -p $TOPDIR/opt/hltd
cp -r $BASEDIR/lib $TOPDIR/opt/hltd

echo "Moving files to their destination"
mkdir -p usr/lib64/$python_dir/site-packages
mkdir -p usr/lib64/$python_dir/site-packages/inotify
mkdir -p usr/lib64/$python_dir/site-packages/elasticsearch
mkdir -p usr/lib64/$python_dir/site-packages/urllib3_hltd

mkdir -p usr/share/hltd-libs-$python_dir

cd $TOPDIR
#urllib3 1.10 (renamed urllib3_hltd)
#cd opt/hltd/lib/urllib3-1.10/
#urllib3 1.24.1 (renamed urllib3_hltd)
cd opt/hltd/lib/urllib3-1.24.1/
$pyexec ./setup.py -q build
$pyexec - <<'EOF'
import compileall
compileall.compile_dir("build/lib/urllib3_hltd",quiet=True)
EOF

$pyexec -O - <<'EOF'
import compileall
compileall.compile_dir("build/lib/urllib3_hltd",quiet=True)
EOF
cp -R build/lib/urllib3_hltd/* $TOPDIR/usr/lib64/$python_dir/site-packages/urllib3_hltd/


cd $TOPDIR
#elasticsearch-py
cd opt/hltd/lib/elasticsearch-py-7.0.0/
$pyexec ./setup.py -q build
$pyexec - <<'EOF'
import compileall
compileall.compile_dir("build/lib/elasticsearch",quiet=True)
EOF
$pyexec -O - <<'EOF'
import compileall
compileall.compile_dir("build/lib/elasticsearch",quiet=True)
EOF
cp -R build/lib/elasticsearch/* $TOPDIR/usr/lib64/$python_dir/site-packages/elasticsearch/


cd $TOPDIR
#_zlibextras library
cd opt/hltd/lib/python-zlib-extras-0.2/
rm -rf build
$pyexec ./setup.py -q build
cp -R build/lib.linux-x86_64-${python_version}/_zlibextras*.so $TOPDIR/usr/lib64/$python_dir/site-packages/


cd $TOPDIR
#python-prctl
cd opt/hltd/lib/python-prctl/
$pyexec ./setup.py -q build
#pyexec - <<'EOF'
$pyexec - <<EOF
import py_compile
py_compile.compile("build/lib.linux-x86_64-${python_version}/prctl.py")
EOF
$pyexec -O - <<EOF
import py_compile
py_compile.compile("build/lib.linux-x86_64-${python_version}/prctl.py")
EOF
cp build/lib.linux-x86_64-${python_version}/*prctl.* $TOPDIR/usr/lib64/$python_dir/site-packages/
#fill egg-info:
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
$pyexec ./setup.py -q build
$pyexec - <<EOF
import compileall
compileall.compile_dir("build/lib.linux-x86_64-${python_version}/inotify",quiet=True)
EOF
$pyexec -O - <<EOF
import compileall
compileall.compile_dir("build/lib.linux-x86_64-${python_version}/inotify",quiet=True)
EOF
cp -R build/lib.linux-x86_64-${python_version}/inotify/* $TOPDIR/usr/lib64/$python_dir/site-packages/inotify/
#fill egg-info:
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
Classifier: Programming Language :: Python :: 2.7
Classifier: Programming Language :: Python :: 3.4
Classifier: Programming Language :: Python :: 3.6
Classifier: Topic :: Software Development :: Libraries :: Python Modules
Classifier: Topic :: System :: Filesystems
Classifier: Topic :: System :: Monitoring
EOF

cd $TOPDIR
cd opt/hltd/lib/setproctitle-1.1.10
$pyexec ./setup.py -q build
cp build/lib.linux-x86_64-${python_version}/setproctitle*.so $TOPDIR/usr/lib64/$python_dir/site-packages/
PROC_FILES="/usr/lib64/${python_dir}/site-packages/setproctitle*.so"
cp COPYRIGHT $TOPDIR/usr/share/hltd-libs-$python_dir/setproctitle-COPYRIGHT

### conditional packaging

SOAPPY_FILES=""
WSTOOLS_FILES=""
ORACLE_FILES=""
PYCACHE_FILES=""

if [ $python_dir = "python3.6" ] || [ $python_dir = "python3.4" ]; then
  cd $TOPDIR
  cd opt/hltd/lib/SOAPpy-py3-0.52.24
  $pyexec ./setup.py -q build
  cp -R build/lib/SOAPpy $TOPDIR/usr/lib64/$python_dir/site-packages/
  SOAPPY_FILES=/usr/lib64/$python_dir/site-packages/SOAPpy

  cd $TOPDIR
  cd opt/hltd/lib/wstools-0.4.8
  $pyexec ./setup.py -q build
  cp -R build/lib/wstools $TOPDIR/usr/lib64/$python_dir/site-packages/
  WSTOOLS_FILES=/usr/lib64/$python_dir/site-packages/wstools

  #Oracle python library
  cd $TOPDIR
  cd opt/hltd/lib/cx_Oracle-7.1/
  rm -rf build
  $pyexec ./setup.py -q build
  cp -R build/lib.linux-x86_64-${python_version}/cx_Oracle*.so $TOPDIR/usr/lib64/$python_dir/site-packages/
  ORACLE_FILES="/usr/lib64/$python_dir/site-packages/cx_Oracle*.so"

  PYCACHE_FILES="/usr/lib64/$python_dir/site-packages/__pycache__"
fi

###

cd $TOPDIR
rm -rf opt

pkgname="hltd-libs"
pypkgprefix="python"
extradeps=""
if [ $python_dir = "python3.6" ]; then
  pypkgprefix="python36"
  pkgname="hltd-libs-python36"
  extradeps=", python36-defusedxml"
fi

if [ $python_dir = "python3.4" ]; then
  pypkgprefix="python34"
  pkgname="hltd-libs-python34"
  extradeps=", python34-defusedxml"
fi



# we are done here, write the specs and make the fu***** rpm
cat > hltd-libs.spec <<EOF
Name: ${pkgname}
Version: 2.6.0
Release: 0
Summary: hlt daemon libraried ${python_dir}
License: gpl
Group: DAQ
Packager: smorovic
Source: none
%define _tmppath $TOPDIR/hltd-build
BuildRoot: %{_tmppath}
BuildArch: $BUILD_ARCH
AutoReqProv: no
#Provides:/usr/lib64/$python_dir/site-packages/prctl.pyc
Requires:${pypkgprefix},libcap,${pypkgprefix}-six >= 1.9,${pypkgprefix}-simplejson >= 3.3.1,${pypkgprefix}-requests $extradeps

%global __python %{__${pythonver}}

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
/usr/share/hltd-libs-$python_dir
/usr/lib64/$python_dir/site-packages/_zlibextras*.so
/usr/lib64/$python_dir/site-packages/python_inotify*
/usr/lib64/$python_dir/site-packages/inotify
/usr/lib64/$python_dir/site-packages/elasticsearch
/usr/lib64/$python_dir/site-packages/urllib3_hltd
/usr/lib64/$python_dir/site-packages/*prctl*
${PROC_FILES}
${SOAPPY_FILES}
${WSTOOLS_FILES}
${PYCACHE_FILES}
${ORACLE_FILES}

EOF
mkdir -p RPMBUILD/{RPMS/{noarch},SPECS,BUILD,SOURCES,SRPMS}
rpmbuild --define "_topdir `pwd`/RPMBUILD" -bb hltd-libs.spec

