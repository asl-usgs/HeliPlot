#!/usr/bin/python
from functools import wraps
import os, re
import subprocess
import signal
import errno

class TimeoutError(Exception):
	pass

class stationNames(object): 
	def timeout(seconds=5, error_message=os.strerror(errno.ETIME)):
		def decorator(func):
			def _handle_timeout(signum, frame):
				raise TimeoutError(error_message)	

			def wrapper(*args, **kwargs):
				signal.signal(signal.SIGALRM, _handle_timeout)
				signal.alarm(seconds)
				try:
					result = func(*args, **kwargs)
				finally:
					signal.alarm(0)
				return result

			return wraps(func)(wrapper)
		return decorator

	def openFiles(self):
		finwrite = open('stationNames.txt', 'w')
		finconfg = open('prestation.cfg', 'r')
		network = []	# list of networks 
		rmnetwork = [] 	# list of networks that will be removed from query list
		for line in finconfg:
			if(line[0] != '#'):
				if line != '\n':
					newline = re.split('=', line)
					if "getmetadata" in newline[0]:
						self.getmetadata = str(newline[1].strip())
					elif "dataless" in newline[0]:
						self.datalesspath = str(newline[1].strip())
					elif "rmnetwork" in newline[0]:
						tmprm = re.split(',', newline[1])
						for i in range(len(tmprm)):
							tmprm[i] = tmprm[i].strip()
							rmnetwork.append(tmprm[i])
							self.rmnetwork = rmnetwork	

	def getLocations(self):
		dirlist = os.listdir(self.datalesspath)
		dirlist.sort()
		listlen = len(dirlist)
		for i in range(listlen):
			print "\n"	
			print dirlist[i]	
			count = 0
			# Remove all networks with rmnetwork key
			# Every line can only have 1 occrurrence within rmnetwork
			for j in range(len(self.rmnetwork)):
				print "dirlist[%d][0:2] = " % i, dirlist[i][0:2]
				print "self.rmnetwork[%d] = " % j, self.rmnetwork[j]
				if dirlist[i][0:2] == self.rmnetwork[j]:
					count = count + 1
					print "break since count = " + str(count) 
					break
				print "count = " + str(count)
				if count == 0:
					try:
						print self.getmetadata + " -sl " + self.datalesspath + dirlist[i]	
						proc = subprocess.Popen([self.getmetadata + " -sl " + self.datalesspath + dirlist[i]], stdout=subprocess.PIPE, shell=True)
						(out, err) = proc.communicate()
						print out
					except Exception as e:
						print "*****Exception found = " + str(e)
					break

if __name__ == '__main__':
	stations = stationNames()
	stations.openFiles()
	stations.timeout()	
	stations.getLocations()	
