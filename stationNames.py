#!/usr/bin/python
import os, re
import multiprocessing
import time
import subprocess
import signal

# ---------------------------------------------------------
# Script uses the getmetadata.py script to parse dataless
# seedfiles for each network. The station names and 
# locations will be extracted and then written to 
# stationNames.txt. This text file will be parsed for the
# networks not contained in the rmnetwork list found in
# prestation.cfg
# ---------------------------------------------------------

# Raises KeyboardInterrupts for multiprocessing methods
class KeyboardInterruptError(Exception): pass	

# Indirect caller for instance methods and multiprocessing
def call_it(instance, name, args=(), kwargs=None):
	if kwargs is None:
		kwargs = {}
	return getattr(instance, name)(*args, **kwargs)

class stationNames(object):
	def __init__(self):
		self.result_list = []	# list of getmetadata results	
		self.getnetwork = []	# list of networks to extract metadata
		self.rmnetwork = []	# list of networks that will be removed from query
		self.getmetadata = ""	# getmetadata executable
		self.datalesspath = ""	# dataless seed path 

	def openFiles(self):
		finconfig = open('prestation.cfg', 'r')
		for line in finconfig:
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
							self.rmnetwork.append(tmprm[i])
						print self.rmnetwork

	def getLocations(self):
		dirlist = os.listdir(self.datalesspath)
		dirlist.sort()
		listlen = len(dirlist)
		for i in range(listlen):
			#print "\n"
			count = 0
			# Remove all networks with rmnetwork key
			# Every line can only have 1 occurrence within rmnetwork
			for j in range(len(self.rmnetwork)):
				tmp = re.split('\\.', dirlist[i])
				network = tmp[0].strip()
				if(network[0] == "_"):
					tmp = re.split('_', network)
					network = tmp[1].strip()
				#print "(network[%d] = " % i, network + ") " + "(self.rmnetwork[%d] = " % j, self.rmnetwork[j] + ") " 
				if network == self.rmnetwork[j]:
					i = i + 1 
					break
				else:
					if j == (len(self.rmnetwork) - 1):
						self.getnetwork.append(dirlist[i])
						i = i + 1
						break
		
		print	
		for x in self.getnetwork:
			print x	
		print

	def getMetadata(self, network):
		try:	
			print self.getmetadata + " -sl " + self.datalesspath + network	
			proc = subprocess.Popen([self.getmetadata + " -sl " + self.datalesspath + network], stdout=subprocess.PIPE, shell=True)
			(out, err) = proc.communicate()
			
			return out
		except KeyboardInterrupt:
			print "KeyboardInterrupt: terminate getMetadata() workers"
			raise KeyboardInterruptError()
		except Exception as e:
			return "*****Exception found = " + str(e)
	
	def log_result(self, result):
		# This is called when getMetadata() returns a result
		# result_list is modified only by the main process, not the pool workers
		self.result_list.append(result)
	
	def parallelMetadata(self):
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		try:	
			print "Start Pool apply_async getMetadata()"	
			async_results = [pool.apply_async(call_it, args=(self, 'getMetadata', (network,)), callback=self.log_result) for network in self.getnetwork]

			pool.close()	
			pool.join()

			stationout = open('stationNames.txt', 'w')
			for result in self.result_list:	
				stationout.write(result)
			
		except KeyboardInterrupt:
			print "Caught KeyboardInterrupt: terminating getMetadata() workers"
			pool.terminate()
			pool.join()
			print "Pool getMetadata() is terminated"
		except Exception, e:
			print "Got exception: %r, terminating the Pool" % (e,)
			pool.terminate()
			pool.join()
			print "Pool getMetadata() is terminated"

if __name__ == '__main__':
	stations = stationNames()
	stations.openFiles()
	stations.getLocations()
	stations.parallelMetadata()
