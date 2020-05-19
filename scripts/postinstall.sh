#!/bin/sh
#this script contains all 'triggerin hltd' actions (all custom scripting that runs on RPM installation)
rm -rf /etc/hltd.instances

#hltd configuration
/opt/fff/init.d/fff configure
#role=\`/opt/fff/setupmachine.py getrole\`

#notofier to update resource count for hltd, triggered at next hltd service restart
touch /opt/hltd/scratch/new-version || true

#notify systemd of updated unit files and enable them (but don't restart except soap2file)
/usr/bin/systemctl daemon-reload

#enable all services with systemd
#TODO: call /opt/fff/init.d/fff enableBoot
/usr/bin/systemctl reenable hltd
/usr/bin/systemctl reenable fff
/usr/bin/systemctl reenable soap2file

#restart soapfile (process will not run if disabled in configuration, but service will be active)
/usr/bin/systemctl restart soap2file

#start hltd if not running (ensures hltd startup on new installation)
rm -rf /var/cache/whitelist.last >& /dev/null || true
rm -rf /var/cache/blacklist.last >& /dev/null || true
/usr/bin/systemctl start hltd
