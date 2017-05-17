hltd
====

The Fcube hlt daemon

Documentation links:

https://twiki.cern.ch/twiki/bin/view/CMS/FCubeMainPage

https://twiki.cern.ch/twiki/bin/view/CMS/FileBasedEvfHLTDaemon

https://twiki.cern.ch/twiki/bin/view/CMS/FFFConfigurationPlan


Building:

required libraries:
yum install -y python-devel libcap-devel rpm-build

building hltd library RPM:
```
scripts/libhltdrpm.sh
```

building hltd executable RPM
```
scripts/hltdrpm.sh
```

building fffmeta RPM:

```
scripts/metarpm scripts/%PARAMFILE%
```

Note: Provide paramfile cache name, which contains last values used. If it does not exist, the file will be created.
"scripts/paramcache.template" is available with default values (note that you need to provide correct password).
For VM build (fffmeta-vm package), paramcache-vm can be used. If no name is provided to the script, it will default to "paramcache" name.
