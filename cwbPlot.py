#!/usr/bin/python
from obspy.neic import Client	# NEIC CWB Server Client for ObsPy
from obspy.core.utcdatetime import UTCDateTime
from obspy import read
from obspy.signal.invsim import evalresp
import re, os, sys, string

# --------------------------------------------------------
# Open seed files from cwbQuery.py and plot
# Pull trace stats from data stream
# --------------------------------------------------------
'''
filelist = os.listdir(seedpath)
filelist = filter(lambda x: not os.path.isdir(x), filelist)
newest = max(filelist, key=lambda x: os.stat(x).st_mtime)
stream = read(newest)
print stream
'''
seedpath = "/home/agonzales/Documents/ObsPy/examples/agonzales/SeedFiles/"
os.chdir(seedpath)
filelist = sorted(os.listdir(seedpath), key=os.path.getctime)
filelen = len(filelist)
i = filelen-1
stream = [0 for x in range(filelen)]	# multidim streams list, streams for each file contain multiple traces so streams = [][] where the second entry denotes the trace index 
print filelen
while i >= 0: 
	stream[i-(filelen-1)] = read(filelist[i], "MSEED")	# read MSEED files from query
	i = i - 1

streamlen = filelen
trace = {}	# dict of traces for each stream
nfft = 0	# number of fft points, necessary for some filtering
for i in range(streamlen):
	strsel = stream[i]	
	tracelen = len(strsel)	# number of traces in stream
	index = str(i)	
	if tracelen == 1:	# single trace stream
		trace[index] = strsel[0]	# trace 0 in stream i
		nfft = trace[index].count()	
	else:			# multiple trace stream
		trace[index] = []	# list in dict 
		nfft = 0
		for j in range(tracelen):	
			trace[index].append(strsel[j])
			tr = trace[index] 	
			nfft = nfft + tr[j].count() 
'''
print "\n"
for i in range(streamlen):
	strsel = stream[i]
	tracelen = len(strsel)
	index = str(i)
	if tracelen == 1:
		print index 
		print trace[index]
	else:
		print index 
		tr = trace[index]	
		for j in range(tracelen):
			print tr[j]	
	print "\n"
'''
