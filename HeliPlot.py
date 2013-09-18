#!/usr/bin/python
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.stream import read
from obspy.signal.invsim import evalresp
from multiprocessing import Manager, Value
import numpy as np
import functools
import multiprocessing
import warnings, glob, re, os, sys, string, subprocess
from datetime import datetime, timedelta
import signal

# Unpack self from arguments and call method cwbQuery()
def unwrap_self_cwbQuery(args, **kwargs):
	return HeliPlot.cwbQuery(*args, **kwargs)

# Unpack self from arguments and call method freqDeconvFilter() 
def unwrap_self_freqDeconvFilter(args, **kwargs):
	return HeliPlot.freqDeconvFilter(*args, **kwargs)

# Unpack self from arguments and call method magnify()
def unwrap_self_magnify(args, **kwargs):
	return HeliPlot.magnify(*args, **kwargs)

# Unpack self from args and call method plotVelocity()
def unwrap_self_plotVelocity(args, **kwargs):
	return HeliPlot.plotVelocity(*args, **kwargs)

# ---------------------------------------------------------
# HeliPlot() uses CWBQuery to query station streams,
# streams are then filtered and plotted using ObsPy
# ---------------------------------------------------------
class HeliPlot(object):
	def cwbQuery(self, station):
		# ------------------------------------------------
		# Pull specific station seed file using CWBQuery
		# ------------------------------------------------
		try:
			proc = subprocess.Popen(["java -jar  " + self.cwbquery + " -s " + '"'+station+'"' + " -b " + '"'+self.datetimeQuery+'"' + " -d " + '"'+str(self.duration)+'"' + " -t ms -o " + self.seedpath+"%N_%y_%j -h " + '"'+self.ipaddress+'"'], stdout=subprocess.PIPE, shell=True)
			(out, err) = proc.communicate()
			print out	
		except Exception as e:
			print "*****Exception found = " + str(e)

	def parallelcwbQuery(self):
		# --------------------------------------------------
		# Initialize all variables needed to run cwbQuery()
		# --------------------------------------------------
		self.home = os.getcwd()
		files = glob.glob(self.seedpath+"*")
		for f in files:
			os.remove(f)	# remove tmp seed files from SeedFiles dir
		stationlen = len(self.stationinfo)

		# -----------------------------------------------
		# Create multiprocessing pools to run multiple 
		# instances of cwbQuery()
		# -----------------------------------------------
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		try:
			pool.map(unwrap_self_cwbQuery, zip([self]*stationlen, self.stationinfo))	
			pool.close()
			pool.join()
			pool.terminate()
			pool.join()
		except KeyboardInterrupt:
			print "Caught KeyboardINterrupt, terminating workers"
			pool.terminate()
			pool.join()
	
	def pullTraces(self):
		# ------------------------------------------------
		# Open seed files from cwbQuery and pull trace
		# stats from the data stream
		# ------------------------------------------------
		os.chdir(self.seedpath)
		filelist = sorted(os.listdir(self.seedpath), key=os.path.getctime)
		self.filelist = filelist	
		filelen = len(filelist)
		stream = [0 for x in range(filelen)]	# multidim streams list, streams for each file contain multiple traces so streams = [][] where the second entry denotes the traces index
		i = filelen - 1
		while i >= 0:
			try:
				stream[i] = read(filelist[i])	# read MSEED files from query
			except Exception as e:
				print "*****Exception found = " + str(e)
			i = i - 1
		streamlen = len(stream)	# number of streams (i.e. stream files)
		self.streamlen = streamlen	
		trace = {}	# dict of traces for each stream
		for i in range(streamlen):
			strsel = stream[i]	# selected stream
			tracelen = len(strsel)	# number of traces in stream
			index = str(i)
			if tracelen == 1:	# single trace stream
				trace[index] = strsel[0]	# trace 0 in stream[i]
			elif tracelen > 1:	# multiple trace stream
				trace[index] = []	# list in dict
				for j in range(tracelen):
					trace[index].append(strsel[j])

		# Loop through stream traces, if trace has sample rate = 0.0Hz
		# => NFFT = 0, then this trace will be removed
		for i in range(streamlen):
			index = str(i)
			tracelen = stream[i].count()
			#print "number of traces = " + str(tracelen)
			#print "len(trace[i]) = " + str(len(trace[index]))
			#print strsel
			if tracelen == 1:
				if trace[index].stats['sampling_rate'] == 0.0:
					stream[i].remove(trace[index])
			elif tracelen > 1:
				for j in range(tracelen):
					if trace[index][j].stats['sampling_rate'] == 0.0:
						stream[i].remove(trace[index][j])
		self.stream = stream

	def freqResponse(self):
		# -----------------------------------------------------------
		# Pull frequency response for station and run a simulation
		# to deconvolve signal, after deconvolution filter signal
		# -----------------------------------------------------------
		networkID = []
		stationID = []
		locationID = []
		channelID = []
		# Need stations listed in SeedFiles directory
		for i in range(self.streamlen):
			tmpstation = self.filelist[i]	
			stationindex = tmpstation.index('_')
			networkID.append(str(tmpstation[0:2]))
			stationID.append(str(tmpstation[2:stationindex]))
			locationindex = len(tmpstation)-11
			channelindex = len(tmpstation)-14
			locationID.append(str(tmpstation[locationindex:locationindex+2]))
			channelID.append(str(tmpstation[channelindex:channelindex+3]))
		self.networkID = networkID
		self.stationID = stationID
		self.locationID = locationID
		self.channelID = channelID

		# -------------------------------------------------------------------
		# Loop through stations and get frequency responses for each stream
		# -------------------------------------------------------------------
		stationName = []	# station names for output plots
		self.resp = []		# station frequency responses for deconvolution	
		for i in range(self.streamlen):
			# NOTE: For aslres01 frequency responses are 
			# contained in /APPS/metadata/RESPS/
			resfilename = "RESP."+networkID[i]+"."+stationID[i]+"."+locationID[i]+"."+channelID[i]	# response filename
			tmpname = re.split('RESP.', resfilename) 	
			stationName.append(tmpname[1].strip())	
			self.stationName = stationName	
			os.chdir(self.resppath)
			resp = {'filename': resfilename, 'date': self.datetimeUTC, 'units': 'VEL'}	# frequency response of data stream in terms of velocity
			self.resp.append(resp)	
			print "stream[%d]" % i
			print "number of traces = " + str(len(self.stream[i]))
			print "datetimeUTC = " + str(self.datetimeUTC)
			print "resfilename = " + str(resfilename)
			print "\n"

	def freqDeconvFilter(self, stream, response):
		# Make sure stream and response names match	
		tmpstr = re.split("\\.", stream[0].getId())
		namestr = tmpstr[1].strip()
		nameres = response['filename'].strip() 
		try:	
			print "Filtering stream " + namestr + " and response " + nameres + "\n" 
			if self.filtertype == "bandpass":
				stream.simulate(paz_remove=None, pre_filt=(self.c1, self.c2, self.c3, self.c4), seedresp=response, taper='True')	# deconvolution
				#stream.filter(self.filtertype, freqmin=self.bplowerfreq, freqmax=self.bpupperfreq, corners=2)	# bandpass filter design
			elif self.filtertype == "lowpass":
				stream.simulate(paz_remove=None, pre_filt=(self.c1, self.c2, self.c3, self.c4), seedresp=response, taper='True')	# deconvolution
				stream.filter(self.filtertype, freq=lpfreq, corners=1)	# lowpass filter design
			elif self.filtertype == "highpass":
				stream.simulate(paz_remove=None, pre_filt=(self.c1, self.c2, self.c3, self.c4), seedresp=response, taper='True')	# deconvolution
				stream.filter(self.filtertype, freq=hpfreq, corners=1)	# highpass filter design	
			
			return stream 
		except Exception as e:
			return "*****Exception found = " + str(e)
	
	def parallelfreqDeconvFilter(self):
		# -------------------------------------------------------------------
		# Simulation/filter for deconvolution
		# NOTE: Filter will be chosen by user, this includes filter 
		# coefficients and frequency ranges. Currently all stations run the
		# same filter design (i.e. bandpass), this will change depending on 
		# the network and data extracted from each station, the higher freq
		# signals will need to use a notch or high freq filter
		# -------------------------------------------------------------------
		# Pre-filter bandpass corner frequencies eliminate end frequency
		# spikes (i.e. H(t) = F(t)/G(t), G(t) != 0)
		# -------------------------------------------------------------------
		for i in range(self.streamlen):	
			self.stream[i].merge(method=0)	# merge traces to eliminate small data lengths, method 0 => no overlap of traces (i.e. overwriting of previous trace data)

		# Deconvolution/Prefilter	
		# Initialize multiprocessing pools
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		try:
			flt_streams = pool.map(unwrap_self_freqDeconvFilter, zip([self]*self.streamlen, self.stream, self.resp))	
			pool.close()
			pool.join()
			pool.terminate()
			pool.join()
			
			return flt_streams	
		except KeyboardInterrupt:
			print "Caught KeyboardInterrupt, terminating workers"
			pool.terminate()
			pool.join()

	def magnify(self, data):
		# --------------------------------------------------------
		# Magnification of trace data 
		# NOTE: Traces are now merged into a single stream so we
		#	must account for this in the magnification
		# --------------------------------------------------------
		data = data * self.magnification
		return data

	def parallelMagnify(self, streams):
		streamlen = len(streams)
		for i in range(streamlen):
			tracelen = streams[i].count()	
			#name = self.networkID[i]+"."+self.stationID[i]+"."+self.locationID[i]+"."+self.channelID[i]	# name
			#print "name = " + str(name)
			#print self.stream[i]
			if tracelen == 1:
				tr = streams[i][0]	# single trace within stream
				data = tr.data		# data samples from single trace	
				datalen = len(data)	# number of data points within single trace
				
				# Initialize multiprocessing pools for magnification	
				cpu_count = multiprocessing.cpu_count()
				PROCESSES = cpu_count
				pool = multiprocessing.Pool(PROCESSES)
				try:
					print "Magnifying stream: " + str(tr.getId()) + "\n"
					magdata = pool.map(unwrap_self_magnify, zip([self]*datalen, data))	# thread trace data 
					np_magdata = np.array(magdata)	# convert list to numpy array to store in trace.data
					streams[i][0].data = np_magdata	# replace trace data with magnified trace data
					pool.close()
					pool.join()
					pool.terminate()
					pool.join()
					
					return streams	
				except KeyboardInterrupt:
					print "Caught KeyboardInterrupt, terminating workers"
					pool.terminate()
					pool.join()
		
	def plotVelocity(self, stream, stationName):
		# --------------------------------------------------------
		# Plot velocity data	
		# --------------------------------------------------------
		stream.merge(method=0)
		print "stream[0].getId() = " + str(stream[0].getId())
		print "stationName = " + str(stationName) + "\n"
		stream.plot(type='dayplot', interval=60,
			vertical_scaling_range=self.vertrange,
			right_vertical_lables=False, number_of_ticks=7,
			one_tick_per_line=True, color=['k'],
			show_y_UTC_label=False, size=(self.resx,self.resy),
			dpi=self.pix, title_size=8,
			title=stream[0].getId()+"  "+"Start Date/Time: "+str(self.datetimeQuery)+"  "+"Filter: "+str(self.filtertype)+"  "+"Vertical Trace Spacing = Ground Vel = 3.33E-4 mm/sec",
			outfile=stationName+"."+self.imgformat)
	
	def parallelPlotVelocity(self, streams):	
		# --------------------------------------------------------
		# Plot velocity data	
		# --------------------------------------------------------
		streamlen = len(streams)	
		os.chdir(self.plotspath)
		imgfiles = glob.glob(self.plotspath+"*")
		for f in imgfiles:
			os.remove(f)	# remove temp jpg files from OutputFiles dir
		#events={"min_magnitude": 6.5}	
		
		print "Plotting velocity data...\n"	
		# Initialize multiprocessing pools for plotting
		cpu_count = multiprocessing.cpu_count()
		PROCESSES = cpu_count
		pool = multiprocessing.Pool(PROCESSES)
		try:
			pool.map(unwrap_self_plotVelocity, zip([self]*streamlen, streams, self.stationName))	# thread plots
			pool.close()
			pool.join()
			pool.terminate()
			pool.join()
		except KeyboardInterrupt:
			print "Caught KeyboardInterrupt, terminating workers"
			pool.terminate()
			pool.join()

	def __init__(self, **kwargs):
		# -----------------------------------------
		# Open cwb config file and read in lines
		# 1) Station info
		# 2) Date/time info for station
		# 3) Duration of signal
		# -----------------------------------------
		fin = open('station.cfg', 'r')
		data = {}	# dict of cwb config data
		data['station'] = []	# list for multiple stations
		STFLAG = False	
		for line in fin:
			if line[0] == '#':
				if line != '\n':
					newline = re.split('#', line)
					if "Station Data" in newline[1]:
						STFLAG = True
			elif line[0] != '#':
				if line != '\n':
					newline = re.split('#', line)	
					if STFLAG:
						data['station'].append(line.strip())
					elif "duration" in newline[1]:
						data['duration'] = newline[0].strip()
					elif "ipaddress" in newline[1]:
						data['ipaddress'] = newline[0].strip()
					elif "httpport" in newline[1]:
						data['httpport'] = newline[0].strip()
					elif "filter" in newline[1]:
						data['filtertype'] = newline[0].strip()
					elif "bplower" in newline[1]:
						data['bplowerfreq'] = newline[0].strip()
					elif "bpupper" in newline[1]:
						data['bpupperfreq'] = newline[0].strip()
					elif "lp" in newline[1]:
						data['lpfreq'] = newline[0].strip()
					elif "hp" in newline[1]:
						data['hpfreq'] = newline[0].strip()
					elif "notch" in newline[1]:
						data['notch'] = newline[0].strip()
					elif "magnification" in newline[1]:
						data['magnification'] = newline[0].strip()
					elif "xres" in newline[1]:
						data['resx'] = newline[0].strip()
					elif "yres" in newline[1]:
						data['resy'] = newline[0].strip()
					elif "pixels" in newline[1]:
						data['pix'] = newline[0].strip()
					elif "image format" in newline[1]:
						data['imgformat'] = newline[0].strip()
					elif "vertical" in newline[1]:
						data['vertrange'] = newline[0].strip()
					elif "c1" in newline[1]:
						data['c1'] = newline[0].strip()
					elif "c2" in newline[1]:
						data['c2'] = newline[0].strip()
					elif "c3" in newline[1]:
						data['c3'] = newline[0].strip()
					elif "c4" in newline[1]:
						data['c4'] = newline[0].strip()
					elif "seed" in newline[1]:
						data['seedpath'] = newline[0].strip()
					elif "plots" in newline[1]:
						data['plotspath'] = newline[0].strip()
					elif "cwbquery" in newline[1]:
						data['cwbquery'] = newline[0].strip()
					elif "responses" in newline[1]:
						data['resppath'] = newline[0].strip()
					
		# Store data in variables
		self.stationdata = data['station']
		self.stationinfo = []
		self.stationlocation = []
		for s in self.stationdata:	
			tmpstation = re.split('\t', s)
			self.stationinfo.append(tmpstation[0].strip())
			self.stationlocation.append(tmpstation[1].strip())
		self.duration = float(data['duration'])
		self.ipaddress = str(data['ipaddress'])
		self.httpport = int(data['httpport'])
		self.filtertype = str(data['filtertype'])
		self.magnification = float(data['magnification'])
		self.resx = int(data['resx'])
		self.resy = int(data['resy'])
		self.pix = int(data['pix'])
		self.imgformat = str(data['imgformat'])	
		self.vertrange = float(data['vertrange'])
		self.c1 = float(data['c1'])
		self.c2 = float(data['c2'])
		self.c3 = float(data['c3'])
		self.c4 = float(data['c4'])
		self.seedpath = str(data['seedpath'])
		self.plotspath = str(data['plotspath'])
		self.cwbquery = str(data['cwbquery'])
		self.resppath = str(data['resppath'])
		if self.filtertype == "bandpass":
			self.bplowerfreq = float(data['bplowerfreq'])
			self.bpupperfreq = float(data['bpupperfreq'])
		elif self.filtertype == "lowpass":
			self.lpfreq = float(data['lpfreq'])
		elif self.filtertype == "highpass":
			self.hpfreq = float(data['hpfreq'])
		elif self.filtertype == "notch":
			self.notch = float(data['notch'])
		
		# Get current date/time and subtract a day
		# this will always pull the current time on the system
		time = datetime.now() - timedelta(days=1)
		timestring = str(time)
		timestring = re.split("\\.", timestring)
		tmp = timestring[0]
		timedate = tmp.replace("-", "/")
		datetimeQuery = timedate.strip()
		#datetimeQuery = "2013/08/17 00:00:00"
		self.datetimeQuery = datetimeQuery
		print "\ndatetimeQuery = " + str(datetimeQuery) + "\n"
		tmpUTC = datetimeQuery
		tmpUTC = tmpUTC.replace("/", "")
		tmpUTC = tmpUTC.replace(" ", "_")
		self.datetimeUTC = UTCDateTime(str(tmpUTC))
	
# -----------------------------
# Main program (can be removed)
# -----------------------------
if __name__ == '__main__':
	heli = HeliPlot()
	heli.parallelcwbQuery()						# query stations
	heli.pullTraces()						# analyze trace data and remove empty traces	
	heli.freqResponse()						# calculate frequency response of signal	
	filtered_streams = heli.parallelfreqDeconvFilter()		# deconvolve/filter trace data	
	magnified_streams = heli.parallelMagnify(filtered_streams)	# magnify trace data 
	heli.parallelPlotVelocity(magnified_streams)			# plot filtered/magnified data	
