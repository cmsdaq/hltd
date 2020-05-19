#!/bin/bash
BASE_FFF=$1
if [ ! -d $BASE_FFF/common ]; then
  #backup location
  BASE_FFF="/opt/offline"
fi

SCRAM_ARCH=$2

CMSSW_VERSION=$3
if [[ $CMSSW_VERSION == *"_patch"* ]]; then
    CMSSW_PKG="cms+cmssw-patch+${CMSSW_VERSION}"
else
    CMSSW_PKG="cms+cmssw+${CMSSW_VERSION}"
fi

#take only first line
out1=`${BASE_FFF}/common/cmspkg -a ${SCRAM_ARCH} rpmenv "rpm -qa --requires ${CMSSW_PKG} | grep ^external+fasthadd+" | sed -n '1p'`

#if empty, bail out
if [[ $out1 == "" ]]; then exit 1; fi;
if [[ $out1 == "\n" ]]; then exit 1; fi;

#extract path from RPM file list
out2=`${BASE_FFF}/common/cmspkg -a ${SCRAM_ARCH} rpmenv "rpm -ql external+fasthadd+2.3-nmpfii6 | grep bin/fastHadd" | grep fastHadd`
#we need parent directory of one containing fastHadd binary
out3=`dirname ${out2}`
out4=`dirname ${out3}`
#strip trailing end of line if present
echo ${out4} | tr -d '\n' | tr -d '\r'

