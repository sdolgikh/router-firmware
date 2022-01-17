import subprocess
import sys

# TODO: вот так можно будет запускать docker build

subprocess.run('/usr/bin/ping 192.168.0.1', shell=True, stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.PIPE)
