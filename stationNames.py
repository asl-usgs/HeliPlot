#!/usr/bin/python
import os, re
import multiprocessing
import time
import subprocess

'''
def getMetadata(func, args):
	result = func(*args)
	print func.__name__
	print args
	print result
	return '%s says that %s%s = %s' % (multiprocessing.current_process().name, func.__name__, args, result)	

def getMetadataStar(args):
	return getMetadata(*args)
'''
def call_it(instance, name, args=(), kwargs=None):
	# Indirect caller for instance methods and multiprocessing"
	if kwargs is None:
		kwargs = {}
	return getattr(instance, name)(*args, **kwargs)

class stationNames(object):
	def __init__(self):
		self.prevnetwork = []	# store previous networks 
		self.rmnetwork = []	# list of networks that will be removed from query list
		self.getmetadata = ""	# getmetadata executable
		self.datalesspath = ""	# dataless seed path
			
	def openFiles(self):
		finwrite = open('stationNames.txt', 'w')
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

	def getLocations(self, network, rmnetwork):
		#" > stationsout.txt"
		tmp = re.split('\\.', network)	
		network = tmp[0].strip()	
		if(network[0] == "_"):
			tmp = network
			tmp = re.split('_', tmp)
			network = tmp[1].strip()
		print "network  = " + str(network)
		print "rmnetwork = " + str(rmnetwork)
		self.prevnetwork.append(network)
		print "self.prevnetwork len = " + str(len(self.prevnetwork))
		count = 0	
		if network[0:2] == rmnetwork:
			count = count + 1	
			print "count = 0: EXIT"	
			print	
			return "count = 0: EXIT"	
		if count == 0:
			print "count != 0: PRINT and EXIT"	
			print	
			return "count != 0: PRINT and EXIT"

	def parallelGetLocations(self):
		dirlist = os.listdir(self.datalesspath)
		dirlist.sort()
		listlen = len(dirlist)
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		#TASKS = [(self.getLocations, (dirlist[i], rmnetwork)) for i in range(listlen) for rmnetwork in self.rmnetwork]	# tasks for multiprocessing pool (need pickle method to call func)
		async_results = [pool.apply_async(call_it, args=(self, 'getLocations', (dirlist[i], rmnetwork))) for i in range(listlen) for rmnetwork in self.rmnetwork]
		pool.close()
		pool.join()	
		map(multiprocessing.pool.ApplyResult.wait, async_results)
		results = [r.get() for r in async_results]
		'''	
		for out in results:	
			print out 
		'''	
		'''
		# Create pool
		try:	
			#imap_it = pool.imap(getMetadataStar, TASKS)	
			#for out in imap_it:
				#print '\t', out
		except Exception as e:
			print "*****Exeption found = " + str(e)
		'''

if __name__ == '__main__':
	stations = stationNames()
	stations.openFiles()
	stations.parallelGetLocations()
