#!/bin/sh
#wrapper for setupmachine.py script. init parameter also fully restores resources
if [[ -n "$1" && $1 == "init" ]]; then
  python2 /opt/fff/setupmachine.py forceConfigure
else 
  python2 /opt/fff/setupmachine.py configure
fi
