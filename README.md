hltd
====

The Fcube hlt daemon

Documentation links:

https://twiki.cern.ch/twiki/bin/view/CMS/FCubeMainPage

https://twiki.cern.ch/twiki/bin/view/CMS/FileBasedEvfHLTDaemon

https://twiki.cern.ch/twiki/bin/view/CMS/FFFConfigurationPlan


Building:

On a (CC7) build machine prerequisite packages need to be installed:
```
yum install -y python-devel libcap-devel rpm-build python-six python-setuptools
```
Note: python 3.4 equivalent is:
```
yum install -y python34-devel libcap-devel rpm-build python34-six python34-setuptools
```

building hltd library RPM:
```
scripts/libhltdrpm.sh
```

building hltd executable RPM:
```
scripts/hltdrpm.sh
```
optionally to only read parameters from cache:
```
scripts/hltdrpm.sh --batch # or -b
```
fffmeta RPM is now merged with hltd RPM and should no longer be built or installed.

Note: Provide as last command line parameter the param cache file containing last values used. If it does not exist, the file will be created.
"scripts/paramcache.template" is available with default values (note that you need to provide correct password).
If no name is provided to the script, default name will be "paramcache". "env":"vm" parameter value is now obsolete with "prod" covering all use cases.
