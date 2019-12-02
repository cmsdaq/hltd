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

#ret=`${BASE_FFF}/common/cmspkg -a ${SCRAM_ARCH} rpmenv "rpm -qa --requires ${CMSSW_PKG} | grep ^external+fasthadd+"`
ret=`${BASE_FFF}/common/cmspkg -a ${SCRAM_ARCH} rpmenv "rpm -qa --requires ${CMSSW_PKG} | grep ^external+fasthadd+" | sed -n '1p'`
if [[ $ret == "" ]]; then exit 1; fi;
if [[ $ret == "\n" ]]; then exit 1; fi;
echo "${BASE_FFF}/${SCRAM_ARCH}/external/${ret}" | tr -d '\n' | tr -d '\r'

