#!/bin/sh
#this script contains all 'triggerin hltd' actions (all custom scripting that runs on RPM installation)
rm -rf /etc/hltd.instances

#hltd configuration
/opt/fff/init.d/fff configure
#role=\`/opt/fff/setupmachine.py getrole\`

#notofier to update resource count for hltd, triggered at next hltd service restart
touch /opt/hltd/scratch/new-version || true

#unregister old sysV style scripts. only soap2file is terminated at this point
/opt/hltd/python/soap2file.py stop || true
/sbin/chkconfig --del hltd >& /dev/null || true
/sbin/chkconfig --del fffmeta >& /dev/null || true
/sbin/chkconfig --del soap2file >& /dev/null || true

#notify systemd of updated unit files and enable them (but don't restart except soap2file)
/usr/bin/systemctl daemon-reload

#enable all services with systemd
#TODO: call /opt/fff/init.d/fff enableBoot
/usr/bin/systemctl reenable hltd
/usr/bin/systemctl reenable fff
/usr/bin/systemctl reenable soap2file

#restart soapfile (process will not run if disabled in configuration, but service will be active)
/usr/bin/systemctl restart soap2file

