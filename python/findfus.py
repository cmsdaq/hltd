#!/bin/env python
import os
import sys
import json
import time


#----------------------------------------------------------------------

def findfus(nostale, nocloud, noquarantined, stale_threshold = 10):
  files = os.listdir('/fff/ramdisk/appliance/boxes')

  try:
    with open('/fff/ramdisk/appliance/blacklist','r') as blf:
      bl = json.load(blf)
  except:
    print "no blacklist file"

  allwhitelist = []
  allwhitelisthlt = []
  whitelist = []
  blacklist = []
  stalelist = []
  cloudlist = []
  qlist = []

  current_time = time.time()

  for f in files:
    if f.startswith('fu-') or f.startswith('dvrubu-') or f.startswith('dvfu-'):
      if f in bl:
        blacklist.append(f)
      else:

        allwhitelist.append(f)
        fu_in_cloud=False
        fu_quarantined=False
        with open('/fff/ramdisk/appliance/boxes/'+f) as boxf:
          boxj = json.load(boxf)
          if boxj['cloud']>0: fu_in_cloud=False
          else:
            if boxj['idles']==0 and boxj['used']==0 and boxj['quarantined']!=0:fu_quarantined=True
        if not fu_in_cloud:
          allwhitelisthlt.append(f)

        if nostale:
          mtime=os.path.getmtime('/fff/ramdisk/appliance/boxes/'+f)
          if current_time - mtime > stale_threshold:
            stalelist.append(f)
            continue

        if nocloud:
          if fu_in_cloud:
            cloudlist.append(f)
            continue
          #otherwise...
        if fu_quarantined:
          qlist.append(f)
          if not noquarantined: whitelist.append(f)
        else:
          whitelist.append(f)

  return dict(
    allwhitelist     = allwhitelist,
    allwhitelisthlt  = allwhitelisthlt,
    whitelist        = whitelist,
    blacklist        = blacklist,      
    stalelist        = stalelist,      
    cloudlist        = cloudlist,      
    qlist            = qlist,      
    )

#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------
if __name__ == '__main__':
  from argparse import ArgumentParser, RawTextHelpFormatter

  parser = ArgumentParser(
    description =
    """
         finds filter units when running on the BU of an appliance
        """,
    formatter_class=RawTextHelpFormatter,
  )

  parser.add_argument("--stale",
                      # note the inverted logic
                      dest = 'nostale',
                      default = True,
                      action = 'store_false',
                      )

  parser.add_argument("--cloud",
                      # note the inverted logic
                      dest = 'nocloud',
                      default = True,
                      action = 'store_false',
                      )

  parser.add_argument("--quarantined",
                      # note the inverted logic
                      dest = 'noquarantined',
                      default = True,
                      action = 'store_false',
                      )

  options = parser.parse_args()

  fu_list = findfus(options.nostale, options.nocloud, options.noquarantined)

  if len(fu_list['blacklist']):
    print "blacklisted   :",','.join(fu_list['blacklist'])
  if len(fu_list['stalelist']):
    print "stale(10s)    :",','.join(fu_list['stalelist'])
  if len(fu_list['cloudlist']):
    print "cloud         :",','.join(fu_list['cloudlist'])
  if len(fu_list['qlist']):
    print "quarantined   :",','.join(fu_list['qlist'])
  if fu_list['whitelist'] != fu_list['allwhitelist']:
    print "usable(HLT)   :",','.join(fu_list['whitelist'])
  if fu_list['allwhitelisthlt'] != fu_list['whitelist']:
    print "whitelist(HLT):",','.join(fu_list['allwhitelisthlt'])
  print "whitelist     :",','.join(fu_list['allwhitelist'])
