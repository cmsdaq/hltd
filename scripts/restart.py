#!/bin/env python
import subprocess
import os
import time

#stop the process
a = subprocess.Popen(["/opt/hltd/init.d/hltd","stop"],close_fds=True)
a.wait()
#exit and let systemd auto restart do the rest of the work (testing needed)
os._exit(0)
