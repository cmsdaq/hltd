#!/bin/env python
import os,sys
import threading
import httplib
import time
import socket
socket.setdefaulttimeout(5)


fu_list=[]

if len(sys.argv)<3:
  print "usage: cloud-switch.py on|off mode=file filepath"
  print "or"
  print "usage: cloud-switch.py on|off fulist"
  sys.exit(1)

if sys.argv[2].startswith("mode=file"):
  #external method to retrieve selection of FUs
  #fi = open('/tmp/CloudConfig/listFuForCloud.txt','r')
  fi = open(sys.argv[3],'r')
  lns = fi.readlines()
  for ln in lns:
      lnf=ln.strip()
      if lnf!="" and lnf!="\n":
        fu_list.append(lnf)
  fi.close()

else:
  fu_list = sys.argv[2].split(',')
#fu-list = sys.argv[2].split()
#fu-list = [sys.argv[2]]

count1 = len(fu_list)
counts = 0
countf = 0

switchover_timeout = 240 #seconds
if sys.argv[1]=="off": switchover_timeout=120

print "Attempting change of cloud mode for max. ",switchover_timeout,"seconds"

failed_connerror=[]
failed_timeout=[]

def do_cloud_onoff(fuhost,cgi,test):

    try:
	global counts
	global countf
	ltimeout = switchover_timeout

        if test==False:
	  conn = httplib.HTTPConnection(host=fuhost,port=9000)
	  conn.request("GET", "/cgi-bin/"+cgi)
	  time.sleep(1)
	  resp = conn.getresponse()
	  conn.close()
	while ltimeout>0:
	    ltimeout-=1
	    conn = httplib.HTTPConnection(host=fuhost,port=9000)
	    conn.request("GET", "/cgi-bin/cloud_mode_active_cgi.py")
	    time.sleep(1)
	    resp = conn.getresponse()
	    conn.close()
	    status = resp.status
	    if status!=200:
		#print "error",fuhost,status
	        failed_connerror.append(fuhost)
		print "failed",fuhost,status
		countf+=1
		return status
	    data = resp.read()
	    if 'exclude' in cgi:
	      if not data.startswith("0"):
		#done
		counts+=1
                return 0
	    elif 'include' in cgi:
	      if data.startswith("0"):
		#done
		counts+=1
                return 0
	    else:
		counts+=1
		return 0
	#print "time expired",fuhost
	failed_timeout.append(fuhost)
	countf+=1
	return -1
    except Exception,ex:
	try:conn.close()
	except:pass
	failed_connerror.append(fuhost)
        countf+=1
        print "failed",fuhost,"exception:",ex
	return -2

t_list = []
#print fu_list
for fu in fu_list:
  time.sleep(.03)
  if sys.argv[1]=="on":
    t = threading.Thread(target=do_cloud_onoff, args = [fu,'exclude_cgi.py',False])
    t.start()
  elif sys.argv[1]=="off":
    t = threading.Thread(target=do_cloud_onoff, args = [fu,'include_cgi.py',False])
    t.start()
  elif sys.argv[1]=="test":
    t = threading.Thread(target=do_cloud_onoff, args = [fu,'',True])
    t.start()
  else:
    print "Please provide on or off as first argument"
    sys.exit(1)
  #t.daemon = True
  t_list.append([fu,t])

#
running = len(t_list)

current_time = time.time()
print "finished notification loop"
print "total:",count1,"success:",counts,"failed:",countf
while running:
  for tpair in t_list:
    if tpair[1]!=None:
      try:
          tpair[1].join(3)
      except:
	  print "exception in joining thread for FU",tpair[0]
      if not tpair[1].isAlive():
        tpair[1]=None
        running-=1
      new_time = time.time()
      if new_time-current_time>3:
        print "total:",count1,"success:",counts,"failed:",countf
        current_time=new_time

print "total:",count1,"success:",counts,"failed:",countf

if countf>0:
  print "timeout checking:",failed_timeout
  print "error connecting:",failed_connerror
else:
	print "success: switched",sys.argv[1],"cloud on all FUs"

