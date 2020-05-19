#!/bin/env /bin/bash
set -x #echo on
TODAY=$(date)
base_dir=${1}
scram_arch=${2}
rel_type=${3}
rel_version=${4}
hltMenu=${5}
runNumber=${6}
#set log file name
logname="/var/log/hltd/pid/hlt_run${runNumber}_pid$$.log"
#override the noclobber option by using >| operator for redirection - then keep appending to log
#echo startRun invoked $TODAY with arguments $1 $2 $3 $4 $5 $6 $7 $8 $9 ${10} ${11} ${12} >| $logname
echo startRun invoked $TODAY with arguments $@ >| $logname
export HOME=/tmp
export SCRAM_ARCH=${scram_arch}
source ${base_dir}/cmsset_default.sh >> $logname
base_dir+=/${scram_arch}/cms/${rel_type}/${rel_version}/src
cd ${base_dir};
pwd >> $logname 2>&1
eval `scram runtime -sh`;
cd ${HOME};
export FRONTIER_LOG_LEVEL="warning"
export FFF_EMPTYLSMODE="true"
export FFF_MICROMERGEDISABLED="true"
if [ ${11} == "None" ]; then
  fileBrokerHost=""
else
  fileBrokerHost=${11}
fi
#exit if executable not found
type -P cmsRun &>/dev/null || (sleep 2;exit 127)
#start CMSSW
exec cmsRun ${hltMenu} "runNumber="${runNumber} "dataDir="${7} "buBaseDir="${8} "numThreads="${9} "numFwkStreams="${10} "fileBrokerHost="${fileBrokerHost} "transferMode="${12}  >> $logname 2>&1
