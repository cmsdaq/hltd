#!/bin/sh

if [ -z $1 ]; then
 echo "Missing fasthadd installation path parameter"
 exit 1
fi

ENV_SCRIPT="${1}/etc/profile.d/init.sh"
FASTHADD="${1}/bin/fastHadd"
#init.sh should provide all necessary environment
#other parameters are forwarded to fastHadd binary
if [ -f $ENV_SCRIPT ]; then
  source ${ENV_SCRIPT}
  if [ -f ${FASTHADD} ]; then
    exec ${FASTHADD} "${@:2}"
    exit # unreachable
  fi
fi

echo "fastHadd not found, make sure external+fasthadd rpm is installed (via cmsdist)"
exit 1
